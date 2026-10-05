/* The workshop presentations' logic (/orientation/ → "Workshop presentations"). The player itself — the pop-up,
   Customize, the presenter view, printing — is src/assets/js/presentations.js; the decks are
   config/presentations/<id>.yml, built into /orientation/presentations/<id>.json (eleventy/filters/presentations.js).
   Pure functions, no DOM: this file only knows about decks, the presenter's own version of one, and text. Tested in
   Node by tests/test_presentations_core.py (the file runs in a vm context, as expenses-core.js does).
   A plain script (no imports, ES2019): it defines window.GVP (globalThis.GVP in Node).

   THE DECK — the JSON file (SPEC §2): { id, title, short, eyebrow, footer, minutes, as_of, built, version, site,
   presets, fillins, live, slides }. A slide: { id, layout, h (a hash of its YAML), part, accent, eyebrow (resolved),
   title, …its layout's fields with the tokens still in them…, notes, minutes, version_minutes?, version_fields?,
   lang?, optional, starts_off, facilitator, handout, version_notes, show_from, show_until, when, data (live slides) }.
   `version_fields`: { <version id>: { <field>: value } } — that version's own words for those fields (an agenda's
   title, an activity's duration …), put in before the presenter's own edits.
   `live`: { key: "text" | { value, steps?, from?, then?, until?, fallback? } } — each of `steps` ([{ from, value }],
   sorted) takes over from its instant `from` (the older { value, from, then } is one such step); from `until` the
   fact is its `fallback`, and so is an empty value ("see aalavina.org …": a readable phrase, never a dangling
   label). The viewer's clock decides (liveText), so a deck opened after a meeting or a price change — or a saved
   copy opened weeks later — already shows the next one. Every key of the map works, whatever the deck file names.
   A live block's `data.rows` hold every row the build knows (about a year): liveRows drops the past ones and then
   applies the slide's `limit` (deadlines: also `limit_each`, per magazine, never cutting an issue's themes apart).

   THE PRESENTER'S VERSION — localStorage["gv-presentations-v1"] (presentations.js reads and writes it; never sent
   anywhere):
     { v: 1, shared: { fill: { key: "text" } },                      the blanks marked `shared` (all four decks)
       decks: { <deck id>: { preset: "<version id>",                 Customize → Version ("" = the first, the full one)
         hidden: [ids], shown: [ids],                                 turned off / on, on top of the version
         order: null | [ids],                                         moved slides (null = the deck's order)
         edits: { <slide id>: { <field>: value, _h: "<the slide's h when it was edited>",
                                _v: { <version id>: { <field>: value } } } },   a field with words of its own in a
                                                                      version (version_fields): kept per version
         added: [{ id: "my-1", layout, title, …its fields…, notes, minutes, after: "<slide id>" }],
         fill: { key: "text" }, checks: { <slide id>: ["0", "2.1"] },  this deck's blanks; ticked checklist items
         last: 12, last_of: 48,                                       the last slide shown (for "Last shown …")
         seen: "<deck version>", seen_built: ISO,                     the deck file the state was last fitted to
         updated: ISO } } }
   normState() makes any stored value safe to use (unknown or broken parts are dropped, never thrown on).

   THE CURRENT VERSION — current(deck, state, presetId, nowMs): every slide in the presenter's order with its edits
   applied, and for each one whether it is in the show and why not:
     a facilitator slide never is (Customize → Prepare) · a slide outside its show_from / show_until days, or a
     `when: "price_notice"` slide while no notice is on, is left out by the clock (never by a switch) · otherwise the
     presenter's own switch (hidden / shown) wins · otherwise the version: `only` lists exactly its slides (also
     ones that start off), `hide` leaves its slides out of the default (no facilitator, no `starts_off`).
   schedule() then gives each slide its minutes in that version (an edited `minutes`, else `version_minutes[preset]`,
   else `minutes`) and its start; the TIME line of the notes and the "you should be at" time come from it, and so do
   the agenda's times (agendaRows: a row with `from` gets the start of the first of its slides still in the show —
   a row whose slides are all left out is dropped — unless the presenter typed a time of their own).

   TEXT — every field may hold **bold**, _italic_ (only at word edges: @alcoholicsanonymous_gv stays as written),
   [label](url) and line breaks, and the tokens {fill:key} {live:key} {slide:id} {ui:key}. The tokens are replaced
   FIRST (subst), then the text is formatted (inline) into a small tree of nodes — text, b, i, a (a checked address
   only: https://, a site path, an e-mail), blank (an empty blank: "[hint]", drawn orange), br, lang (a span in
   another language: {lang:es}…{/lang}) — which the player turns into elements with textContent. Nothing here is
   ever HTML, and nothing the presenter types becomes HTML.
   {slide:id} is that slide's NUMBER in the current version (the decks write the word: "slide {slide:x}");
   "(not in this version)" when it is not in the show. {ui:customize} is the name of one of the player's controls
   in the PAGE's language (the notes are English; on /es/ they say "Personalizar", marked as Spanish). A notes_only
   blank never shows its value on a slide. A notes line may start with {only:a,b} or {not:a,b} (version ids): it is
   in the notes of only those versions, or of all but those (noteLines).

   THE "MY VERSION" FILE (Customize → Save & share): { app: "gv-presentation-version", v: 1, deck, deck_title,
   deck_version, exported, preset, hidden, shown, order, edits, added, fill, shared, checks }. validateImport()
   is strict — the right app and deck, sizes, known layouts and fields, strings (never HTML) — and says why not.

   AN UPDATED DECK (the committee changes a slide later): reconcile() keeps every edit by slide id, drops what
   belongs to slides that are gone, and lists the edits whose `_h` differs from the slide's new `h` ("Changed since
   you edited it": Use the new version → dropEdit / Keep mine → keepEdit). New slides take their default place,
   also inside a presenter's own order. A state last fitted to a NEWER deck file (another window got it first) is
   left as it is: newerSeen() tells the player to fetch that file instead of pruning the slides it does not know. */
(function (root) {
  "use strict";

  var VERSION = "1.0.0";
  var SCHEMA = 1;
  var STORAGE_KEY = "gv-presentations-v1";
  var FILE_APP = "gv-presentation-version";
  var LAYOUTS = ["title", "section", "bullets", "columns", "table", "agenda", "quote", "activity", "qa", "resources",
    "credits", "closing", "text", "flow", "live"];
  // what Customize → Add a slide makes: Title & points · Text · Section break · Discussion question
  var ADD_LAYOUTS = ["bullets", "text", "section", "qa"];
  var ACCENTS = ["gv", "lv", "vine", "grape", "navy"];
  var PRINT_MODES = ["slides", "notes", "handout", "script"];
  var ID = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
  var MY_ID = /^my-[1-9][0-9]{0,5}$/;
  var KEY = /^[a-z][a-z0-9_]*$/;
  var CHECK = /^[0-9]{1,3}(?:\.[0-9]{1,3})?$/;
  var HASH = /^[0-9A-Za-z_-]{1,64}$/;
  var HTML = /<[A-Za-z!\/?]/;
  var EMAIL_FULL = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$/;
  // An empty blank inside a substituted string: private-use characters the formatter turns into a "blank" node.
  // They are taken out of every value put into a text, so nothing typed can fake one.
  var BLANK_OPEN = "\uE000", BLANK_CLOSE = "\uE001";
  var PRIVATE = /[\uE000\uE001]/g;
  // Sizes a "my version" file (and a stored state) may have: generous for a real deck (the committee meeting has
  // ~70 blanks and 43 slides), small enough that a strange file cannot slow the page down.
  var LIMITS = { fileBytes: 2000000, text: 4000, long: 20000, list: 80, cells: 8, added: 60, ids: 800, fill: 400,
    fillText: 600, checks: 200, versions: 20 };

  /* The words the player writes ON the slides and in the notes. The presentations' content stays English (the
     owner's decision: on /es/ the controls are Spanish and the slides are marked "(en inglés)"), so these are
     English on both pages — like the decks themselves. The controls' own words are src/_i18n/presentations.json. */
  var EN = {
    left_out: "(not in this version)",
    current_as_of: "Current as of {date}",
    minute: "minute",
    minutes: "minutes",
    you_need: "You will need",
    none: "Nothing is listed right now. See {url}",
    see: "see {where}",
    online: "Online",
    online_on: "Online on {platform}",
    tentative: "Details to be confirmed",
    zoom_id: "Zoom ID",
    passcode: "Passcode",
    meeting_id: "Meeting ID",
    contact: "Contact",
    gv: "Grapevine",
    lv: "La Viña",
    magazine: "Magazine",
    issue: "Issue",
    theme: "Theme",
    due: "Stories due",
    print: "Print",
    digital: "Digital",
    one_year: "1 year, U.S.",
    from_date: "from {date}",
    new_prices: "New prices from {date}",
    books_more: "Books: {amount} more each",
    botm_also: "Also",
    // after an English gloss that is a machine translation (a La Viña theme's English words), as the site marks one
    auto_translated: "auto-translated",
    time: "TIME: about {about}{opt}. You should be at about {at} when you move on.",
    time_optional: " (optional: it can go when you're running late)",
    seconds: "{n} seconds",
    about_minute: "1 minute",
    about_minutes: "{n} minutes",
    disclaimer: [
      "Not an official AA Grapevine, Inc. presentation.",
      "Prepared by the NETA 65 Grapevine & La Viña Committee for local service use. It is not A.A. Conference-approved literature and does not speak for A.A. as a whole or for AA Grapevine, Inc.",
    ],
    // {ui:<key>}: the player's controls by their English names (the player hands the page language's names to
    // subst as ctx.ui; these are what a key says without them)
    ui: {
      customize: "Customize", version: "Version", slides: "Slides", edit: "Edit", add: "Add", your_details: "Your details",
      prepare: "Prepare", save_share: "Save & share", notes: "Notes", overview: "Overview", presenter_view: "Presenter view",
      print: "Print", full_screen: "Full screen", black_screen: "Black screen",
    },
  };
  // A live block's rows when the slide names no `limit` (SPEC §1's live kinds)
  var LIMIT = { deadlines: 6, events: 5, meeting: 3, "lv-workshop": 3, monthly: 3, bulletin: 3 };

  /* ------------------------------------------------------------------ small helpers */
  function isMap(v) { return !!v && typeof v === "object" && !Array.isArray(v); }
  function isStr(v) { return typeof v === "string"; }
  function isNum(v) { return typeof v === "number" && isFinite(v); }
  function has(o, k) { return isMap(o) && Object.prototype.hasOwnProperty.call(o, k); }
  function copy(v) { return v === undefined ? undefined : JSON.parse(JSON.stringify(v)); }
  function pad2(n) { return (n < 10 ? "0" : "") + n; }
  function uniq(list) {
    var out = [];
    for (var i = 0; i < list.length; i++) if (out.indexOf(list[i]) < 0) out.push(list[i]);
    return out;
  }
  function fmt(s, vars) {
    return String(s).replace(/\{(\w+)\}/g, function (m, k) { return vars && vars[k] !== undefined && vars[k] !== null ? String(vars[k]) : m; });
  }
  function ms(v) {
    if (v === null || v === undefined || v === "") return NaN;
    var t = typeof v === "number" ? v : Date.parse(String(v));
    return isFinite(t) ? t : NaN;
  }
  function slideId(s) { return isStr(s) && (ID.test(s) || MY_ID.test(s)); }

  /* ------------------------------------------------------------------ facts of the day */
  function textOf(v) { return isStr(v) ? v : isNum(v) ? String(v) : ""; }
  /** One {live:…} value at the instant nowMs: a string as it is; a map → its `value`, or the last of its `steps`
   *  (and the old `then`) whose `from` has come; from `until` on — and whenever that text is empty — its `fallback`
   *  (or ""). noFallback: the bare value ("" when there is none: whether a price notice is on). */
  function liveText(v, nowMs, noFallback) {
    if (isStr(v)) return v;
    if (isNum(v)) return String(v);
    if (!isMap(v)) return "";
    var now = isNum(nowMs) ? nowMs : Date.now();
    var fallback = noFallback ? "" : textOf(v.fallback);
    var until = ms(v.until);
    if (isFinite(until) && now >= until) return fallback;
    var text = textOf(v.value);
    var at = -Infinity;
    var steps = Array.isArray(v.steps) ? v.steps.slice() : [];
    if (has(v, "then")) steps.push({ from: v.from, value: v.then });
    steps.forEach(function (s) {
      // the latest step that has begun (the list is sorted, but a later `from` wins whatever the order)
      var t = isMap(s) ? ms(s.from) : NaN;
      if (isFinite(t) && t <= now && t >= at && (isStr(s.value) || isNum(s.value))) { at = t; text = textOf(s.value); }
    });
    return text || fallback;
  }
  /** Every key of a deck's `live` map, as text at nowMs (generic: a key the build adds later works too). */
  function liveValues(live, nowMs) {
    var out = {};
    if (!isMap(live)) return out;
    Object.keys(live).forEach(function (k) { if (KEY.test(k)) out[k] = liveText(live[k], nowMs); });
    return out;
  }
  /** Is a price-change notice on (the build's price_change_note is that notice's words, and empty without one)? */
  function noticeOn(live, nowMs) { return !!liveText(isMap(live) ? live.price_change_note : "", nowMs, true); }
  /** Is a slide in the show at nowMs, by the clock: its show_from / show_until (instants: the first and the last
   *  moment of those Central days) and `when: "price_notice"`. */
  function inWindow(slide, nowMs, live) {
    var now = isNum(nowMs) ? nowMs : Date.now();
    var from = ms(slide && slide.show_from), until = ms(slide && slide.show_until);
    if (isFinite(from) && now < from) return false;
    if (isFinite(until) && now > until) return false;
    if (slide && slide.when === "price_notice" && !noticeOn(live, now)) return false;
    return true;
  }

  /* ------------------------------------------------------------------ the stored state */
  function emptyState() { return { v: 1, shared: { fill: {} }, decks: {} }; }
  function emptyDeck() {
    return { preset: "", hidden: [], shown: [], order: null, edits: {}, added: [], fill: {}, checks: {}, last: 0, last_of: 0, seen: "", seen_built: "", updated: "" };
  }
  function cleanText(v, max) {
    if (!isStr(v)) return null;
    v = v.replace(PRIVATE, "");
    return v.length > (max || LIMITS.text) ? v.slice(0, max || LIMITS.text) : v;
  }
  // While validateImport checks a file, text that looks like HTML refuses it ("strings only — never HTML"). What the
  // presenter typed on this device is kept as typed: the player only ever draws text, so "<3" or "<b>" shows as
  // those characters (dropping it on the next visit would lose their words).
  var STRICT = false;
  function cleanFill(m) {
    var out = {};
    if (!isMap(m)) return out;
    Object.keys(m).slice(0, LIMITS.fill).forEach(function (k) {
      var v = cleanText(m[k], LIMITS.fillText);
      if (KEY.test(k) && v !== null && !(STRICT && HTML.test(v))) out[k] = v;
    });
    return out;
  }
  function cleanIds(list) {
    return Array.isArray(list) ? uniq(list.filter(slideId)).slice(0, LIMITS.ids) : [];
  }
  /** A deck's stored part, made safe: wrong types and unknown fields are dropped; values are checked like an
   *  imported file's (cleanEdit / cleanAdded: types, sizes, known fields — HTML-looking text is refused only in a
   *  file), so what is stored can always be drawn. */
  function normDeck(raw) {
    var d = emptyDeck();
    if (!isMap(raw)) return d;
    if (isStr(raw.preset) && (raw.preset === "" || ID.test(raw.preset))) d.preset = raw.preset;
    d.hidden = cleanIds(raw.hidden);
    d.shown = cleanIds(raw.shown).filter(function (x) { return d.hidden.indexOf(x) < 0; });
    d.order = Array.isArray(raw.order) ? cleanIds(raw.order) : null;
    if (d.order && !d.order.length) d.order = null;
    if (Array.isArray(raw.added)) {
      var seen = {};
      raw.added.slice(0, LIMITS.added).forEach(function (a) {
        var c = cleanAdded(a);
        if (c.ok && !seen[c.slide.id]) { seen[c.slide.id] = 1; d.added.push(c.slide); }
      });
    }
    if (isMap(raw.edits)) {
      Object.keys(raw.edits).slice(0, LIMITS.ids).forEach(function (id) {
        if (!slideId(id)) return;
        var e = cleanEdit(raw.edits[id], null);
        if (e.ok && Object.keys(e.edit).length) d.edits[id] = e.edit;
      });
    }
    d.fill = cleanFill(raw.fill);
    if (isMap(raw.checks)) {
      Object.keys(raw.checks).slice(0, LIMITS.ids).forEach(function (id) {
        var v = raw.checks[id];
        if (slideId(id) && Array.isArray(v)) {
          var ok = uniq(v.filter(function (x) { return isStr(x) && CHECK.test(x); })).slice(0, LIMITS.checks);
          if (ok.length) d.checks[id] = ok;
        }
      });
    }
    if (isNum(raw.last) && raw.last >= 1) d.last = Math.floor(raw.last);
    if (isNum(raw.last_of) && raw.last_of >= 1) d.last_of = Math.floor(raw.last_of);
    if (isStr(raw.seen) && raw.seen.length <= 64) d.seen = raw.seen;
    if (isStr(raw.seen_built) && raw.seen_built.length <= 40) d.seen_built = raw.seen_built;
    if (isStr(raw.updated) && raw.updated.length <= 40) d.updated = raw.updated;
    return d;
  }
  /** The whole stored value, made safe (anything unreadable → an empty state; never throws). */
  function normState(raw) {
    var s = emptyState();
    if (isStr(raw)) {
      try { raw = JSON.parse(raw); } catch (e) { return s; }
    }
    if (!isMap(raw)) return s;
    s.shared.fill = cleanFill(raw.shared && raw.shared.fill);
    if (isMap(raw.decks)) {
      Object.keys(raw.decks).forEach(function (id) { if (ID.test(id)) s.decks[id] = normDeck(raw.decks[id]); });
    }
    return s;
  }
  /** A deck's part of the state (made when missing: the caller saves only when something changes). */
  function deckState(state, id) {
    if (!isMap(state.decks)) state.decks = {};
    if (!isMap(state.decks[id])) state.decks[id] = emptyDeck();
    return state.decks[id];
  }
  /** What the presenter changed in a deck (the page's status line, "Reset" shown or not). */
  function summary(ds, deck) {
    ds = ds || emptyDeck();
    var firstPreset = deck && deck.presets && deck.presets[0] ? deck.presets[0].id : "";
    var details = Object.keys(ds.fill || {}).filter(function (k) { return String(ds.fill[k]).trim(); }).length;
    var checks = 0;
    Object.keys(ds.checks || {}).forEach(function (k) { checks += ds.checks[k].length; });
    var out = {
      preset: ds.preset && ds.preset !== firstPreset ? ds.preset : "",
      hidden: (ds.hidden || []).length,
      shown: (ds.shown || []).length,
      edited: Object.keys(ds.edits || {}).length,
      added: (ds.added || []).length,
      moved: !!(ds.order && ds.order.length),
      details: details,
      checks: checks,
      last: ds.last || 0,
      last_of: ds.last_of || 0,
    };
    out.changed = !!(out.preset || out.hidden || out.shown || out.edited || out.added || out.moved);
    out.any = out.changed || !!details || !!checks;
    return out;
  }
  function sharedCount(state) {
    var f = (state && state.shared && state.shared.fill) || {};
    return Object.keys(f).filter(function (k) { return String(f[k]).trim(); }).length;
  }

  /* ------------------------------------------------------------------ the fields a presenter can edit */
  // kind: line (one line) · text (lines kept) · list (one per line) · outline (one per line; two spaces in front =
  // a sub-item) · num · cells (one row of a table, "a | b | c") · table (rows of cells) · links (label | url | note)
  // · flow (title | text) · columns · agenda (the last two have their own small forms in the player)
  var LAYOUT_FIELDS = {
    title: [["subtitle", "text"], ["lines", "list"]],
    section: [["number", "line"], ["subtitle", "text"]],
    bullets: [["items", "outline"]],
    columns: [["columns", "columns"]],
    table: [["header", "cells"], ["rows", "table"]],
    agenda: [["items", "agenda"]],
    quote: [["quote", "text"], ["credit", "line"]],
    activity: [["steps", "outline"], ["duration", "num"], ["materials", "list"]],
    qa: [["prompts", "list"], ["note", "text"]],
    resources: [["links", "links"]],
    credits: [["sources", "list"], ["note", "text"]],
    closing: [["message", "text"], ["lines", "list"]],
    text: [["body", "text"]],
    flow: [["steps", "flow"]],
    live: [["intro", "text"]],
  };
  // the full-page layouts (title, section, closing) have no takeaway box and no sources line
  var NO_TAIL = { title: 1, section: 1, closing: 1 };
  /** [[field, kind], …] a slide of `layout` can have edited, in the order the form shows them. */
  function fieldsOf(layout) {
    if (!has(LAYOUT_FIELDS, layout)) return [];
    var out = [["title", "line"], ["eyebrow", "line"]].concat(LAYOUT_FIELDS[layout]);
    if (!NO_TAIL[layout]) out = out.concat([["takeaway", "text"], ["source", "line"]]);
    return out.concat([["minutes", "num"], ["notes", "text"]]);
  }
  function kindOf(layout, field) {
    var f = fieldsOf(layout);
    for (var i = 0; i < f.length; i++) if (f[i][0] === field) return f[i][1];
    return "";
  }

  // Checking one value of a field (an import, a stored edit): the cleaned value, or undefined when it is not one.
  function cText(v, max) {
    if (!isStr(v) || v.length > (max || LIMITS.text) || (STRICT && HTML.test(v))) return undefined;
    return v.replace(PRIVATE, "");
  }
  function cList(v, item) {
    if (!Array.isArray(v) || v.length > LIMITS.list) return undefined;
    var out = [];
    for (var i = 0; i < v.length; i++) {
      var x = item(v[i]);
      if (x === undefined) return undefined;
      out.push(x);
    }
    return out;
  }
  function cOutlineItem(v) {
    if (isStr(v)) return cText(v);
    if (!isMap(v) || Object.keys(v).some(function (k) { return k !== "text" && k !== "items"; })) return undefined;
    var t = cText(v.text);
    if (t === undefined) return undefined;
    if (!has(v, "items")) return { text: t };
    var sub = cList(v.items, function (x) { return cText(x); });
    return sub === undefined ? undefined : { text: t, items: sub };
  }
  function cMap(v, fields, required) {
    if (!isMap(v)) return undefined;
    var out = {};
    var keys = Object.keys(v);
    for (var i = 0; i < keys.length; i++) {
      var k = keys[i];
      if (!has(fields, k)) return undefined;
      var x = fields[k](v[k]);
      if (x === undefined) return undefined;
      out[k] = x;
    }
    for (var j = 0; j < (required || []).length; j++) if (!has(out, required[j])) return undefined;
    return out;
  }
  var str = function (v) { return cText(v); };
  var CHECKERS = {
    line: function (v) { return cText(v, 600); },
    text: function (v) { return cText(v, LIMITS.long); },
    list: function (v) { return cList(v, str); },
    outline: function (v) { return cList(v, cOutlineItem); },
    num: function (v) { return isNum(v) && v >= 0 && v <= 600 ? v : isStr(v) && v.length <= 20 && !(STRICT && HTML.test(v)) ? v : undefined; },
    cells: function (v) { return Array.isArray(v) && v.length <= LIMITS.cells ? cList(v, str) : undefined; },
    table: function (v) {
      return cList(v, function (r) {
        return Array.isArray(r) && r.length <= LIMITS.cells ? cList(r, function (c) { return isNum(c) ? String(c) : cText(c); }) : undefined;
      });
    },
    links: function (v) { return cList(v, function (x) { return cMap(x, { label: str, url: str, note: str }, ["label"]); }); },
    flow: function (v) { return cList(v, function (x) { return cMap(x, { title: str, text: str }, ["title"]); }); },
    columns: function (v) {
      return cList(v, function (x) {
        return cMap(x, {
          heading: str, gloss: str, text: function (t) { return cText(t, LIMITS.long); },
          items: function (i) { return cList(i, cOutlineItem); },
          accent: function (a) { return ACCENTS.indexOf(a) >= 0 ? a : undefined; },
          link: str,
        });
      });
    },
    agenda: function (v) { return cList(v, function (x) { return cMap(x, { time: str, title: str, detail: str, from: str }); }); },
  };
  // "number" of a section may be a number in the deck file (1, 2 …) or text ("A")
  function checkValue(kind, field, v) {
    if (field === "number") return isNum(v) ? v : cText(v, 12);
    if (field === "minutes" || field === "duration") return isNum(v) && v >= 0 && v <= 240 ? v : undefined;
    return has(CHECKERS, kind) ? CHECKERS[kind](v) : undefined;
  }
  /** One stored or imported edit (a slide's changed fields + `_h`, and `_v`: the fields edited in one version only)
   *  → { ok, edit, error }. With a layout, only that layout's fields are allowed (an import, a deck that changed);
   *  without one, any known field of any layout. `inner`: the fields of one version (no `_h` or `_v` of their own). */
  function cleanEdit(raw, layout, inner) {
    if (!isMap(raw)) return { ok: false, error: "pres.err.bad_edit" };
    var out = {};
    var keys = Object.keys(raw);
    for (var i = 0; i < keys.length; i++) {
      var k = keys[i];
      if (k === "_h" && !inner) {
        if (isStr(raw._h) && HASH.test(raw._h)) out._h = raw._h;
        continue;
      }
      if (k === "_v" && !inner) {
        var vs = raw._v, pids = isMap(vs) ? Object.keys(vs) : null;
        if (!pids || pids.length > LIMITS.versions) return { ok: false, error: "pres.err.bad_edit", field: k };
        var byVersion = {};
        for (var n = 0; n < pids.length; n++) {
          if (!ID.test(pids[n])) return { ok: false, error: "pres.err.bad_edit", field: k };
          var one = cleanEdit(vs[pids[n]], layout, true);
          if (!one.ok) return one;
          if (Object.keys(one.edit).length) byVersion[pids[n]] = one.edit;
        }
        if (Object.keys(byVersion).length) out._v = byVersion;
        continue;
      }
      // without a layout, a field may be any of the kinds its name has ("items" of bullets is an outline, of an
      // agenda its rows; "steps" of an activity or a flow): the first kind that takes the value
      var kinds = layout ? [kindOf(layout, k)].filter(Boolean) : kindsOf(k);
      if (!kinds.length) return { ok: false, error: "pres.err.bad_edit", field: k };
      var v = undefined;          // (a `var` would otherwise keep the previous field's value)
      for (var j = 0; j < kinds.length && v === undefined; j++) v = checkValue(kinds[j], k, raw[k]);
      if (v === undefined) return { ok: false, error: HTML.test(JSON.stringify(raw[k])) ? "pres.err.html" : "pres.err.bad_edit", field: k };
      out[k] = v;
    }
    return { ok: true, edit: out };
  }
  function kindsOf(field) {
    var out = [];
    LAYOUTS.forEach(function (l) {
      var k = kindOf(l, field);
      if (k && out.indexOf(k) < 0) out.push(k);
    });
    return out;
  }
  /** One added slide → { ok, slide, error }: an id "my-N", one of the layouts Add makes, its fields, `after`. */
  function cleanAdded(raw) {
    if (!isMap(raw) || !isStr(raw.id) || !MY_ID.test(raw.id) || ADD_LAYOUTS.indexOf(raw.layout) < 0) return { ok: false, error: "pres.err.bad_added" };
    var fields = {};
    Object.keys(raw).forEach(function (k) { if (k !== "id" && k !== "layout" && k !== "after") fields[k] = raw[k]; });
    var e = cleanEdit(fields, raw.layout);
    if (!e.ok) return { ok: false, error: e.error, field: e.field };
    delete e.edit._h;
    var slide = { id: raw.id, layout: raw.layout };
    Object.keys(e.edit).forEach(function (k) { slide[k] = e.edit[k]; });
    if (!isStr(slide.title)) slide.title = "";
    slide.after = isStr(raw.after) && slideId(raw.after) ? raw.after : "";
    return { ok: true, slide: slide };
  }

  /* ------------------------------------------------------------------ the current version */
  function presetOf(deck, id) {
    var list = (deck && Array.isArray(deck.presets)) ? deck.presets : [];
    for (var i = 0; i < list.length; i++) if (list[i] && list[i].id === id) return list[i];
    return list[0] || { id: "", hide: [], only: null };
  }
  /** Is a deck slide in this version before the presenter's own switches (facilitator slides never are)? */
  function inPreset(slide, preset) {
    if (!slide || slide.facilitator) return false;
    if (preset && Array.isArray(preset.only)) return preset.only.indexOf(slide.id) >= 0;
    if (slide.starts_off) return false;
    return !(preset && Array.isArray(preset.hide) && preset.hide.indexOf(slide.id) >= 0);
  }
  function deckIds(deck) { return ((deck && deck.slides) || []).map(function (s) { return s.id; }); }

  /** The deck's order with the added slides at their places: each right after its `after` slide (the newest first
   *  when several follow one slide — "after the current one"); one whose slide is gone goes last. */
  function defaultOrder(deck, ds) {
    var order = deckIds(deck);
    var added = (ds && ds.added) || [];
    var pending = added.slice();
    var guard = 0;
    while (pending.length && guard++ < 200) {
      var rest = [];
      pending.forEach(function (a) {
        var at = order.indexOf(a.after);
        if (at >= 0) order.splice(at + 1, 0, a.id);
        else rest.push(a);
      });
      if (rest.length === pending.length) break;
      pending = rest;
    }
    pending.forEach(function (a) { if (order.indexOf(a.id) < 0) order.push(a.id); });
    return order;
  }
  /** The presenter's order: their `order` (ids that still exist), with every slide it does not name — a slide the
   *  committee added since, a slide added by the presenter — put back at its default place (right after the slide
   *  that comes before it there). */
  function orderOf(deck, ds) {
    var dflt = defaultOrder(deck, ds);
    if (!ds || !Array.isArray(ds.order) || !ds.order.length) return dflt;
    var known = {};
    dflt.forEach(function (id) { known[id] = 1; });
    var out = uniq(ds.order.filter(function (id) { return known[id]; }));
    dflt.forEach(function (id, i) {
      if (out.indexOf(id) >= 0) return;
      var at = -1;
      for (var j = i - 1; j >= 0 && at < 0; j--) at = out.indexOf(dflt[j]);
      out.splice(at + 1, 0, id);
    });
    return out;
  }
  // an added slide's own fields (it inherits its part and colours from the slide before it; a Q&A slide has no eyebrow
  // unless the presenter types one, as the build gives the deck's own: eleventy/filters/presentations.js)
  function addedSlide(a, prev, deck) {
    var s = copy(a);
    delete s.after;
    s.h = "";
    s.part = prev ? prev.part : null;
    s.accent = prev ? prev.accent : "gv";
    if (!isStr(s.eyebrow) || !s.eyebrow.trim()) {
      s.eyebrow = s.layout === "qa" ? ""
        : prev && prev.part ? "Part " + prev.part.n + " · " + prev.part.title : String((deck && deck.eyebrow) || "");
      s._eyebrow_default = true;
    }
    if (!isStr(s.notes)) s.notes = "";
    if (!isNum(s.minutes)) s.minutes = 1;
    s.optional = false; s.starts_off = false; s.facilitator = false; s.handout = false;
    s.version_notes = {}; s.show_from = null; s.show_until = null; s.when = null; s.data = null;
    return s;
  }

  /**
   * The presentation as it will be shown: { deck, ds, preset, live, list, shown, byId, nowMs, total }.
   *   list   every slide in the presenter's order: { id, src (the deck's slide, or the added one), slide (src with
   *          the edits applied), added, edited: [fields], stale (edited before the committee changed it), shown,
   *          why ("" | "facilitator" | "window" | "hidden" | "starts_off" | "version"), base (in the version before
   *          the presenter's switches), n (its number, when shown), start / mins / end (minutes; see schedule) }
   *   shown  the entries in the show, in order (n = 1, 2 …)
   */
  function current(deck, state, presetId, nowMs) {
    var now = isNum(nowMs) ? nowMs : Date.now();
    // the deck's part of the state itself, made safe IN PLACE (the same object stays in the state): what Customize
    // changes through cur.ds is stored, also after another current() of the same deck
    var ds = emptyDeck();
    if (isMap(state)) {
      if (!isMap(state.decks)) state.decks = {};
      var raw = state.decks[deck.id];
      var norm = normDeck(raw);
      if (isMap(raw)) {
        Object.keys(raw).forEach(function (k) { delete raw[k]; });
        Object.keys(norm).forEach(function (k) { raw[k] = norm[k]; });
        ds = raw;
      } else ds = state.decks[deck.id] = norm;
    }
    var preset = presetOf(deck, isStr(presetId) && presetId ? presetId : ds.preset);
    // lookups by id without a prototype: an id or key such as "constructor" is unknown, as any other would be
    var byDeck = Object.create(null);
    (deck.slides || []).forEach(function (s) { byDeck[s.id] = s; });
    var byAdded = Object.create(null);
    ds.added.forEach(function (a) { byAdded[a.id] = a; });
    var list = [];
    var byId = Object.create(null);
    var prev = null;
    orderOf(deck, ds).forEach(function (id) {
      var src = byDeck[id];
      var added = !src;
      var slide;
      if (added) {
        if (!byAdded[id]) return;
        src = addedSlide(byAdded[id], prev, deck);
        slide = copy(src);
      } else slide = inVersion(copy(src), preset.id);
      var edit = ds.edits[id];
      var edited = [];
      if (edit) {
        // the edits of every version, then the ones made in this version (a field with words of its own here)
        var mine = isMap(edit._v) && preset.id && has(edit._v, preset.id) && isMap(edit._v[preset.id]) ? edit._v[preset.id] : {};
        [edit, mine].forEach(function (m) {
          Object.keys(m).forEach(function (k) {
            if (k === "_h" || k === "_v" || !kindOf(slide.layout, k)) return;
            slide[k] = copy(m[k]);
            if (edited.indexOf(k) < 0) edited.push(k);
          });
        });
        if (edited.indexOf("eyebrow") >= 0) delete slide._eyebrow_default;
      }
      var fac = !!slide.facilitator;
      var win = fac || inWindow(slide, now, deck.live);
      var base = added ? true : inPreset(slide, preset);
      var user = ds.hidden.indexOf(id) >= 0 ? false : ds.shown.indexOf(id) >= 0 ? true : null;
      var shown = !fac && win && (user === null ? base : user);
      var why = shown ? "" : fac ? "facilitator" : !win ? "window" : user === false ? "hidden" : slide.starts_off && !(preset && Array.isArray(preset.only)) ? "starts_off" : "version";
      // "Changed since you edited it": an edit in this version or in another one (Use the new version drops both)
      var anyEdit = edited.length > 0 || (!!edit && isMap(edit._v) && Object.keys(edit._v).length > 0);
      var e = {
        id: id, src: src, slide: slide, added: added, edited: edited,
        stale: !added && !!edit && anyEdit && isStr(edit._h) && edit._h !== src.h,
        shown: shown, why: why, base: base && !fac && win, user: user, n: null, start: 0, mins: 0, end: 0,
      };
      list.push(e);
      byId[id] = e;
      if (!fac) prev = slide;
    });
    var shown = list.filter(function (e) { return e.shown; });
    shown.forEach(function (e, i) { e.n = i + 1; });
    var cur = { deck: deck, ds: ds, preset: preset, live: liveValues(deck.live, now), list: list, shown: shown, byId: byId, nowMs: now, total: 0 };
    schedule(cur);
    return cur;
  }

  /** A deck slide's own words in a version: its version_fields[preset] in place of those fields (the presenter's
   *  edits come on top of them). Changes and returns `slide` (a copy). */
  function inVersion(slide, presetId) {
    var all = slide && slide.version_fields;
    var vf = isMap(all) && isStr(presetId) && presetId && has(all, presetId) ? all[presetId] : null;
    if (!isMap(vf)) return slide;
    Object.keys(vf).forEach(function (k) {
      if (kindOf(slide.layout, k) && vf[k] !== null && vf[k] !== undefined) slide[k] = copy(vf[k]);
    });
    return slide;
  }
  /** Has a deck slide words of its own for `field` in some version (version_fields)? The presenter's edit of such a
   *  field stays in the version it was made in (setField); any other edit applies to every version. */
  function versioned(src, field) {
    var all = src && src.version_fields;
    return isMap(all) && Object.keys(all).some(function (p) {
      return isMap(all[p]) && has(all[p], field) && all[p][field] !== null && all[p][field] !== undefined;
    });
  }
  /** What a field of a deck slide says in a version before any edit of the presenter's (its version_fields, else
   *  the deck's own; minutes: as the schedule counts them there). */
  function versionValue(src, field, presetId) {
    var s = inVersion(copy(src), presetId);
    return field === "minutes" ? minutesOf({ slide: s, edited: [] }, presetId) : s[field];
  }
  /** A slide's minutes in a version: an edited `minutes` wins, then version_minutes[preset], then `minutes`. */
  function minutesOf(entry, presetId) {
    var s = entry.slide || entry;
    if (entry.edited && entry.edited.indexOf("minutes") >= 0 && isNum(s.minutes)) return s.minutes;
    var vm = s.version_minutes;
    if (isMap(vm) && presetId && isNum(vm[presetId])) return vm[presetId];
    return isNum(s.minutes) ? s.minutes : 0;
  }
  /** Each shown slide's start, minutes and end in the current version (in minutes from the start); a slide not in
   *  the show gets the start of the next one shown (so an agenda row pointing at it still has a time). */
  function schedule(cur) {
    var t = 0;
    cur.shown.forEach(function (e) {
      e.mins = minutesOf(e, cur.preset && cur.preset.id);
      e.start = t;
      t += e.mins;
      e.end = t;
    });
    var next = t;
    for (var i = cur.list.length - 1; i >= 0; i--) {
      var e = cur.list[i];
      if (e.shown) next = e.start;
      else { e.start = next; e.end = next; e.mins = 0; }
    }
    cur.total = t;
    return cur;
  }
  /** Minutes from the start → "h:mm" (0:08, 1:15), to the nearest minute. */
  function clock(min) {
    var m = Math.max(0, Math.round(Number(min) || 0));
    return Math.floor(m / 60) + ":" + pad2(m % 60);
  }
  /** "1½ minutes", "1 minute", "45 seconds" — the pptx notes' own way of saying it. */
  function aboutText(min) {
    var m = Number(min) || 0;
    if (m < 1) return fmt(EN.seconds, { n: Math.max(5, Math.round((m * 60) / 5) * 5) });
    var whole = Math.floor(m);
    var q = Math.round((m - whole) * 4);
    if (q === 4) { whole += 1; q = 0; }
    if (!q) return whole === 1 ? EN.about_minute : fmt(EN.about_minutes, { n: whole });
    return fmt(EN.about_minutes, { n: whole + ["", "¼", "½", "¾"][q] });
  }
  /** The notes' TIME line for a shown slide in the current version (English, like the notes). */
  function timeLine(entry) {
    if (!entry || !entry.shown) return "";
    return fmt(EN.time, { about: aboutText(entry.mins), opt: entry.slide.optional ? EN.time_optional : "", at: clock(entry.end) });
  }
  /** {slide:id} → its number in the current version, "(left out of this version)", or null for an unknown id. */
  function slideRef(cur, id) {
    var e = cur && cur.byId[id];
    if (!e) return null;
    return e.shown ? String(e.n) : EN.left_out;
  }

  /** An agenda slide's rows in the current version: [{ time, title, detail, from, auto }]. A row with `from` gets
   *  the start of the first of its slides still in the show (its slides: from its `from` up to the next row's) and
   *  is dropped when they are all left out; a time the presenter typed for it wins. Rows without `from` keep the
   *  time they have. */
  function agendaRows(entry, cur, opts) {
    // opts.all: keep the rows the version leaves out too, marked `dropped` (the agenda's editor: one row per item)
    var all = !!(opts && opts.all);
    var items = Array.isArray(entry.slide.items) ? entry.slide.items : [];
    var editedItems = entry.edited.indexOf("items") >= 0;
    var pos = {};
    cur.list.forEach(function (e, i) { pos[e.id] = i; });
    var rows = items.map(function (it) {
      it = isMap(it) ? it : { title: String(it) };
      return { it: it, at: isStr(it.from) && has(pos, it.from) ? pos[it.from] : -1 };
    });
    var out = [];
    rows.forEach(function (r, i) {
      var it = r.it;
      var typed = editedItems && isStr(it.time) && it.time.trim() ? it.time.trim() : "";
      var row = { time: isStr(it.time) ? it.time : "", title: isStr(it.title) ? it.title : "", detail: isStr(it.detail) ? it.detail : "", from: isStr(it.from) ? it.from : "", auto: false };
      if (r.at >= 0) {
        var end = cur.list.length;
        for (var j = i + 1; j < rows.length; j++) if (rows[j].at > r.at) { end = rows[j].at; break; }
        var first = null;
        for (var k = r.at; k < end && !first; k++) if (cur.list[k].shown) first = cur.list[k];
        row.computed = first ? clock(first.start) : "";
        if (!first) {
          if (!all) return;
          row.dropped = true;
        }
        if (typed) row.time = typed;
        else if (first) { row.time = row.computed; row.auto = true; }
      } else if (editedItems) row.time = isStr(it.time) ? it.time : "";
      out.push(row);
    });
    return out;
  }

  /** The agenda editor's rows ([{ time, title, detail, from }]) say what the version's own agenda (`items`) says:
   *  every row as the deck has it, the rows with `from` left to the clock (no time typed) — no edit to store. A
   *  time typed for such a row is an edit, even one equal to the computed time (it would stop following the
   *  version). */
  function agendaUnchanged(rows, items) {
    var str = function (v) { return isStr(v) ? v : ""; };
    items = Array.isArray(items) ? items : [];
    if (!Array.isArray(rows) || rows.length !== items.length) return false;
    return rows.every(function (r, i) {
      var it = isMap(items[i]) ? items[i] : { title: String(items[i]) };
      if (!isMap(r) || str(r.title) !== str(it.title) || str(r.detail) !== str(it.detail) || str(r.from) !== str(it.from)) return false;
      return str(it.from) ? !str(r.time).trim() : str(r.time) === str(it.time);
    });
  }

  /* ------------------------------------------------------------------ blanks */
  function fillDefs(deck) {
    // no prototype: {fill:constructor} is an unknown blank (it stays as written), not Object's own property
    var out = Object.create(null);
    ((deck && deck.fillins) || []).forEach(function (f) { if (f && KEY.test(f.key) && isMap(f.label)) out[f.key] = f; });
    return out;
  }
  /** A blank's value: the presenter's (the shared one for a `shared` blank), else the deck's default, else "". */
  function fillValue(deck, state, key) {
    var def = fillDefs(deck)[key];
    if (!def) return "";
    var src = def.shared ? state && state.shared && state.shared.fill : state && state.decks && state.decks[deck.id] && state.decks[deck.id].fill;
    var v = src && has(src, key) ? String(src[key]) : "";
    if (!v.trim() && isStr(def.default)) v = def.default;
    return v.replace(PRIVATE, "").trim();
  }
  var FILL_RE = /\{fill:([a-z][a-z0-9_]*)\}/g;
  /** The fill keys a value names (any field, any depth; not the other versions' words: the current version's are
   *  already in the slide's fields). */
  function fillsIn(v, out) {
    out = out || [];
    if (isStr(v)) {
      var m;
      FILL_RE.lastIndex = 0;
      while ((m = FILL_RE.exec(v))) if (out.indexOf(m[1]) < 0) out.push(m[1]);
    } else if (Array.isArray(v)) v.forEach(function (x) { fillsIn(x, out); });
    else if (isMap(v)) Object.keys(v).forEach(function (k) { if (k !== "data" && k !== "version_fields") fillsIn(v[k], out); });
    return out;
  }
  /** "Your details", grouped by the slide each blank is first on (the presenter's order): [{ entry | null, keys }];
   *  blanks no slide names are last (entry null). */
  function fillGroups(cur) {
    var defs = fillDefs(cur.deck);
    var placed = {};
    var groups = [];
    cur.list.forEach(function (e) {
      var keys = fillsIn(e.slide).filter(function (k) { return defs[k] && !placed[k]; });
      if (!keys.length) return;
      keys.forEach(function (k) { placed[k] = 1; });
      groups.push({ entry: e, keys: keys });
    });
    var rest = Object.keys(defs).filter(function (k) { return !placed[k]; });
    // the deck's own order of its blanks inside each group
    var order = ((cur.deck && cur.deck.fillins) || []).map(function (f) { return f.key; });
    groups.forEach(function (g) { g.keys.sort(function (a, b) { return order.indexOf(a) - order.indexOf(b); }); });
    if (rest.length) groups.push({ entry: null, keys: rest.sort(function (a, b) { return order.indexOf(a) - order.indexOf(b); }) });
    return groups;
  }
  /** The blanks still empty on the slides of the show (not the notes: the room never sees those), in show order. */
  function emptyBlanks(cur, state) {
    var defs = fillDefs(cur.deck);
    var out = [];
    cur.shown.forEach(function (e) {
      var s = {};
      Object.keys(e.slide).forEach(function (k) { if (k !== "notes" && k !== "version_notes" && k !== "data") s[k] = e.slide[k]; });
      fillsIn(s).forEach(function (k) {
        if (defs[k] && !defs[k].notes_only && out.indexOf(k) < 0 && !fillValue(cur.deck, state, k)) out.push(k);
      });
    });
    return out;
  }

  /* ------------------------------------------------------------------ text */
  /** The tokens of one text replaced: ctx { deck, state, live (liveValues), cur (for {slide:…}), where: "slide" |
   *  "notes", ui: { key: "the control's name" } and lang (the page's) for {ui:…} }. An empty blank becomes
   *  BLANK_OPEN + hint + BLANK_CLOSE; an unknown token stays as written. */
  function subst(text, ctx) {
    if (!isStr(text)) text = text === null || text === undefined ? "" : String(text);
    ctx = ctx || {};
    var defs = ctx.defs || (ctx.defs = fillDefs(ctx.deck));
    var out = text.replace(PRIVATE, "").replace(/\{(fill|live|slide|ui):([^}]*)\}/g, function (m, kind, key) {
      if (kind === "fill") {
        var def = defs[key];
        if (!def) return m;
        var hint = String(def.hint || key).replace(PRIVATE, "");
        // a first name only in the speaker's own notes (anonymity): never on a slide, whatever is typed
        if (def.notes_only && ctx.where !== "notes") return BLANK_OPEN + hint + BLANK_CLOSE;
        var v = fillValue(ctx.deck, ctx.state, key);
        return v ? v : BLANK_OPEN + hint + BLANK_CLOSE;
      }
      if (kind === "live") {
        var live = ctx.live || {};
        return has(live, key) ? String(live[key]).replace(PRIVATE, "") : m;
      }
      if (kind === "ui") {
        if (!has(EN.ui, key)) return m;
        var name = isMap(ctx.ui) && has(ctx.ui, key) && isStr(ctx.ui[key]) ? ctx.ui[key] : EN.ui[key];
        // the English notes name the page's own buttons: on /es/ "Personalizar", read out in Spanish
        var lang = isStr(ctx.lang) && /^[a-z]{2}$/.test(ctx.lang) && ctx.lang !== "en" && name !== EN.ui[key] ? ctx.lang : "";
        name = name.replace(PRIVATE, "").replace(/[{}]/g, "");
        return lang ? "{lang:" + lang + "}" + name + "{/lang}" : name;
      }
      var r = ctx.cur ? slideRef(ctx.cur, key) : null;
      return r === null ? m : r;
    });
    return out.indexOf(EN.left_out) >= 0 ? tidyLeftOut(out) : out;
  }
  // A sentence that pointed at slides the version leaves out ("Part 2's history (slides {slide:a}–{slide:b}; …)",
  // "the tours ({slide:c}–{slide:d}, skip both)") reads as one "(not in this version)", not as a run of them.
  var LO = EN.left_out.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  var LO_RANGE = new RegExp("(" + LO + ")\\s*[–-]\\s*" + LO, "g");
  var LO_WORD = new RegExp("\\bslides?\\s+(" + LO + ")", "g");
  var LO_WRAPPED = new RegExp("\\((" + LO + ")\\)", "g");
  var LO_OPEN = new RegExp("\\(" + LO.replace(/\\\)$/, "") + "\\)([,;])", "g");
  function tidyLeftOut(s) {
    var inner = EN.left_out.slice(0, -1);              // "(not in this version"
    return s.replace(LO_RANGE, "$1").replace(LO_WORD, "$1").replace(LO_WRAPPED, "$1").replace(LO_OPEN, inner + "$1");
  }

  var LANG_OPEN = /^\{lang:(es|en)\}/;
  var WORD = /[\p{L}\p{N}_]/u;
  function isWord(c) { return !!c && WORD.test(c); }
  function isSpace(c) { return !c || /\s/.test(c); }
  /** A link's address → its href, or null when it is not one we follow: https://…, mailto:…, an e-mail, or a
   *  page of the site written from its first slash ("/contribute/#deadlines" → the site's base path, with /es/
   *  on the Spanish page). opts: { base: "/aagrapevine/", lang }. */
  function safeHref(url, opts) {
    var u = String(url || "").trim();
    opts = opts || {};
    if (/^https:\/\/[^\s"<>`]+$/i.test(u)) return u;
    if (/^mailto:[^\s"<>`]+$/i.test(u)) return u;
    if (EMAIL_FULL.test(u)) return "mailto:" + u;
    if (/^\/(?!\/)[^\s"<>`\\]*$/.test(u)) {
      var base = String(opts.base || "/").replace(/\/+$/, "");
      return base + (opts.lang === "es" ? "/es" : "") + u;
    }
    return null;
  }
  /** An address as the slide writes it out: "aagrapevine.org/podcasts", "neta65.github.io/aagrapevine/events/". */
  function showUrl(url, siteHost) {
    var u = String(url || "").trim();
    if (/^\/(?!\/)/.test(u)) return String(siteHost || "").replace(/\/+$/, "") + u;
    return u.replace(/^mailto:/i, "").replace(/^https?:\/\//i, "").replace(/^www\./i, "").replace(/\/$/, "");
  }

  /**
   * Inline formatting of a text whose tokens are already replaced → nodes:
   *   { t: "text", v } · { t: "b", c: [nodes] } · { t: "i", c } · { t: "a", href, c } · { t: "blank", v } · { t: "br" }
   *   · { t: "lang", lang, c }
   * **bold** · _italic_ (an underscore opens only after a non-word character and closes only before one, so
   * snake_case and @handle_names stay as written) · [label](address) (an address safeHref refuses is shown as plain
   * text) · a line break · {lang:es}words in Spanish{/lang} (to the end of the text when it is not closed). Unmatched
   * marks are plain text.
   */
  function inline(text, opts) {
    var s = isStr(text) ? text : String(text === null || text === undefined ? "" : text);
    return parseInline(s, opts || {}, 0);
  }
  function parseInline(s, opts, depth) {
    var out = [];
    var buf = "";
    function flush() { if (buf) { out.push({ t: "text", v: buf }); buf = ""; } }
    var i = 0;
    while (i < s.length) {
      var c = s.charAt(i);
      if (c === BLANK_OPEN) {
        var e = s.indexOf(BLANK_CLOSE, i + 1);
        if (e > i) { flush(); out.push({ t: "blank", v: s.slice(i + 1, e) }); i = e + 1; continue; }
        i++; continue;
      }
      if (c === BLANK_CLOSE) { i++; continue; }
      if (c === "\n") { flush(); out.push({ t: "br" }); i++; continue; }
      if (c === "{" && depth < 6) {
        var lm = LANG_OPEN.exec(s.slice(i, i + 12));
        if (lm) {
          // the span ends at its {/lang} (the next one, after any nested span's) or with the text
          var from = i + lm[0].length, close2 = -1, level = 1;
          var re = /\{lang:(?:es|en)\}|\{\/lang\}/g;
          re.lastIndex = from;
          var mm;
          while ((mm = re.exec(s))) {
            level += mm[0] === "{/lang}" ? -1 : 1;
            if (!level) { close2 = mm.index; break; }
          }
          flush();
          out.push({ t: "lang", lang: lm[1], c: parseInline(close2 < 0 ? s.slice(from) : s.slice(from, close2), opts, depth + 1) });
          i = close2 < 0 ? s.length : close2 + 7;
          continue;
        }
        if (s.slice(i, i + 7) === "{/lang}") { i += 7; continue; }      // a stray end mark: nothing to show
      }
      if (depth < 6 && c === "*" && s.charAt(i + 1) === "*" && !isSpace(s.charAt(i + 2))) {
        var close = s.indexOf("**", i + 2);
        while (close > i + 2 && isSpace(s.charAt(close - 1))) close = s.indexOf("**", close + 1);
        if (close > i + 2) {
          flush();
          out.push({ t: "b", c: parseInline(s.slice(i + 2, close), opts, depth + 1) });
          i = close + 2;
          continue;
        }
      }
      if (depth < 6 && c === "_" && !isWord(s.charAt(i - 1)) && !isSpace(s.charAt(i + 1)) && s.charAt(i + 1) !== "_") {
        var j = i + 2, end = -1;
        while (j < s.length) {
          if (s.charAt(j) === "_" && !isSpace(s.charAt(j - 1)) && !isWord(s.charAt(j + 1))) { end = j; break; }
          if (s.charAt(j) === "\n") break;
          j++;
        }
        if (end > i + 1) {
          flush();
          out.push({ t: "i", c: parseInline(s.slice(i + 1, end), opts, depth + 1) });
          i = end + 1;
          continue;
        }
      }
      if (depth < 6 && c === "[") {
        var m = /^\[([^\]\n]+)\]\(([^)\s]+)\)/.exec(s.slice(i));
        if (m) {
          flush();
          var href = safeHref(m[2], opts);
          var label = parseInline(m[1], opts, depth + 1);
          if (href) out.push({ t: "a", href: href, c: label });
          else out.push.apply(out, label);
          i += m[0].length;
          continue;
        }
      }
      buf += c;
      i++;
    }
    flush();
    return out;
  }
  /** subst then inline: what a field of a slide becomes. */
  function rich(text, ctx) { return inline(subst(text, ctx), ctx); }
  /** The plain text of nodes (a title read by the live region, a print header). */
  function plain(nodes) {
    var out = "";
    (nodes || []).forEach(function (n) {
      if (n.t === "text") out += n.v;
      else if (n.t === "blank") out += "[" + n.v + "]";
      else if (n.t === "br") out += " ";
      else if (n.c) out += plain(n.c);
    });
    return out;
  }
  // A notes line's label: SAY: · DO: · IF TIME, ASK: · FACILITATOR TIP: · RUNNING LATE? · 20-MINUTE VERSION (…):
  // · EN ESPAÑOL (…): — capitals with Spanish accents too
  var LABEL = /^((?:[A-Z0-9ÁÉÍÓÚÑÜ][A-Z0-9ÁÉÍÓÚÑÜ'’.&\/]*)(?:[ ,–-]+[A-Z0-9ÁÉÍÓÚÑÜ][A-Z0-9ÁÉÍÓÚÑÜ'’.&\/]*)*(?:\s+\([^)\n]{1,90}\))?[:?])\s+([\s\S]*)$/;
  var VERSION_MARK = /^\{(only|not):([^}]*)\}\s*/;
  /** The notes, one paragraph per line, each with its label apart (drawn bold): [{ label, text }]. A line that
   *  starts with {only:a,b} is kept only in those versions (presetId), one with {not:a,b} in every other one. */
  function noteLines(notes, presetId) {
    return String(notes || "").replace(/\r\n?/g, "\n").split("\n").map(function (l) { return l.trim(); }).filter(Boolean).map(function (l) {
      var v = VERSION_MARK.exec(l);
      if (v) {
        var named = v[2].split(",").map(function (x) { return x.trim(); }).indexOf(isStr(presetId) ? presetId : "") >= 0;
        if (v[1] === "only" ? !named : named) return null;
        l = l.slice(v[0].length);
        if (!l.trim()) return null;
      }
      // a whole line in Spanish ({lang:es}SAY: …{/lang}): its label stays apart, the rest keeps the mark
      var lang = LANG_OPEN.exec(l);
      var m = LABEL.exec(lang ? l.slice(lang[0].length) : l);
      if (m) return { label: m[1], text: (lang ? lang[0] : "") + m[2] };
      return { label: "", text: l };
    }).filter(Boolean);
  }

  /* ------------------------------------------------------------------ live blocks */
  function past(iso, now, slack) {
    var t = ms(iso);
    return isFinite(t) && t + (slack || 0) < now;
  }
  function count(v) {
    var n = isStr(v) && /^\d{1,2}$/.test(v) ? Number(v) : v;
    return isNum(n) && n >= 1 && n <= 50 && Math.floor(n) === n ? n : 0;
  }
  /** Cuts `rows` after `n`, but never between rows of one group (an issue's themes): the last group kept stays whole. */
  function cutWhole(rows, n, groupOf) {
    if (!n || rows.length <= n) return rows;
    var g = groupOf(rows[n - 1]);
    var end = n;
    while (end < rows.length && groupOf(rows[end]) === g) end++;
    return rows.slice(0, end);
  }
  /**
   * The rows a live block shows at nowMs (deadlines, events, meeting, lv-workshop, bulletin; monthly's tips): the
   * build sends every row it knows, and the viewer's clock leaves out the past ones before the slide's limits apply
   * — so a copy opened weeks later still lists what is next. `limit` comes from the block's data or the slide's
   * options (else the kind's own number); deadlines take `limit_each` instead when there is one (that many of EACH
   * magazine, 3 + 3, in date order) and keep an issue's themes together (`issue_key`) whatever the limit. Meetings
   * and workshops go once they end (`end`; without it two hours after they start). Events: a monthly series (rows
   * with the same `series`: the CityWide booth's Saturdays) shows once, its first date still to come, before the
   * limit — unless the block's data or the slide's options say `series: "all"` (a list of every date).
   */
  function liveRows(kind, data, options, nowMs) {
    var d = isMap(data) ? data : {};
    var o = isMap(options) ? options : {};
    var now = isNum(nowMs) ? nowMs : Date.now();
    var rows = (Array.isArray(kind === "monthly" ? d.tips : d.rows) ? (kind === "monthly" ? d.tips : d.rows) : []).filter(isMap);
    var limit = count(has(d, "limit") ? d.limit : o.limit) || LIMIT[kind] || 0;
    if (kind === "deadlines") {
      var issue = function (r) { return String(r.pub || "") + "|" + String(r.issue_key || r.issue || "") + "|" + String(r.issue_key ? "" : r.due || ""); };
      rows = rows.filter(function (r) { return !past(r.due, now); });
      var each = count(has(d, "limit_each") ? d.limit_each : o.limit_each);
      if (!each) return cutWhole(rows, limit, issue);
      var pubs = [];
      rows.forEach(function (r) { if (pubs.indexOf(r.pub) < 0) pubs.push(r.pub); });
      var keep = [];
      pubs.forEach(function (p) {
        keep = keep.concat(cutWhole(rows.filter(function (r) { return r.pub === p; }), each, issue));
      });
      return rows.filter(function (r) { return keep.indexOf(r) >= 0; });
    }
    if (kind === "events") {
      rows = rows.filter(function (r) { return !past(r.end || r.start, now); });
      if ((has(d, "series") ? d.series : o.series) !== "all") {
        var seen = Object.create(null);
        rows = rows.filter(function (r) {
          var id = isStr(r.series) ? r.series.trim() : "";
          if (!id) return true;                    // a one-off event
          if (seen[id]) return false;
          seen[id] = 1;
          return true;
        });
      }
    } else if (kind === "meeting" || kind === "lv-workshop") {
      rows = rows.filter(function (r) { return r.end ? !past(r.end, now) : !past(r.start, now, 2 * 3600 * 1000); });
    }
    return limit ? rows.slice(0, limit) : rows;
  }

  /* ------------------------------------------------------------------ editing */
  /** A field's value as the text of its form control (the line-based kinds). */
  function toText(kind, v) {
    if (v === null || v === undefined) return "";
    switch (kind) {
      case "list":
        return Array.isArray(v) ? v.map(String).join("\n") : String(v);
      case "outline":
        if (!Array.isArray(v)) return String(v);
        return v.map(function (it) {
          if (!isMap(it)) return String(it);
          return [String(it.text || "")].concat((it.items || []).map(function (x) { return "  " + x; })).join("\n");
        }).join("\n");
      case "cells":
        return Array.isArray(v) ? v.map(String).join(" | ") : String(v);
      case "table":
        return Array.isArray(v) ? v.map(function (r) { return (Array.isArray(r) ? r : [r]).map(String).join(" | "); }).join("\n") : "";
      case "links":
        return Array.isArray(v) ? v.map(function (x) { return [x.label || "", x.url || ""].concat(x.note ? [x.note] : []).join(" | "); }).join("\n") : "";
      case "flow":
        return Array.isArray(v) ? v.map(function (x) { return [x.title || ""].concat(x.text ? [x.text] : []).join(" | "); }).join("\n") : "";
      case "num":
        return isNum(v) ? String(v) : String(v);
      default:
        return String(v);
    }
  }
  function lines(t) { return String(t || "").replace(/\r\n?/g, "\n").split("\n"); }
  function cells(l) { return l.split("|").map(function (c) { return c.trim(); }); }
  /** A form control's text → the field's value (undefined: leave the field out). */
  function fromText(kind, text) {
    var t = String(text === null || text === undefined ? "" : text).replace(PRIVATE, "");
    switch (kind) {
      case "line":
        return t.replace(/\s*\n\s*/g, " ").trim();
      case "text":
        return t.replace(/\r\n?/g, "\n").replace(/[ \t]+$/gm, "").replace(/^\n+|\n+$/g, "");
      case "list":
        return lines(t).map(function (l) { return l.trim(); }).filter(Boolean);
      case "outline": {
        var out = [];
        lines(t).forEach(function (l) {
          if (!l.trim()) return;
          var sub = /^(?: {2,}|\t)/.test(l);
          var v = l.trim().replace(/^[-•]\s+/, "");
          var last = out[out.length - 1];
          if (sub && last !== undefined) {
            if (!isMap(last)) out[out.length - 1] = last = { text: last, items: [] };
            last.items.push(v);
          } else out.push(v);
        });
        return out;
      }
      case "num": {
        var n = parseFloat(t.replace(",", "."));
        return isFinite(n) && n >= 0 ? Math.min(240, Math.round(n * 100) / 100) : undefined;
      }
      case "cells":
        return t.trim() ? cells(t.replace(/\n/g, " ")) : [];
      case "table":
        return lines(t).filter(function (l) { return l.trim(); }).map(cells);
      case "links":
        return lines(t).filter(function (l) { return l.trim(); }).map(function (l) {
          var c = cells(l);
          var o = { label: c[0] || "", url: c[1] || "" };
          if (c.length > 2 && c.slice(2).join(" | ")) o.note = c.slice(2).join(" | ");
          return o;
        });
      case "flow":
        return lines(t).filter(function (l) { return l.trim(); }).map(function (l) {
          var c = cells(l);
          var o = { title: c[0] || "" };
          if (c.length > 1 && c.slice(1).join(" | ")) o.text = c.slice(1).join(" | ");
          return o;
        });
      default:
        return t;
    }
  }
  function same(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
  /** Sets one field of a slide in the presenter's version (or of their added slide). A value equal to what the
   *  slide says in the version being edited (presetId; default: the presenter's version) without an edit drops the
   *  edit of that field — typing a version's own minutes or title back is no edit; anything else is stored. An
   *  edit applies to every version, except one of a field the slide has its own words for in some version
   *  (version_fields: an agenda, an activity's time …): that one is kept for the version being edited only
   *  (edits[id]._v[version]), so the other versions keep their own words. The edit remembers the slide's `h` (to
   *  tell "Changed since you edited it"); "Reset this slide" (resetSlide) takes every version's edits away. */
  function setField(deck, ds, id, field, value, presetId) {
    var added = null;
    for (var i = 0; i < ds.added.length; i++) if (ds.added[i].id === id) added = ds.added[i];
    if (added) {
      if (!kindOf(added.layout, field)) return false;
      if (value === undefined || value === null) delete added[field];
      else added[field] = copy(value);
      return true;
    }
    var src = null;
    (deck.slides || []).forEach(function (s) { if (s.id === id) src = s; });
    if (!src || !kindOf(src.layout, field)) return false;
    var e = ds.edits[id] || {};
    var pid = isStr(presetId) && presetId ? presetId : presetOf(deck, ds.preset).id;
    var none = value === undefined || value === null || same(value, versionValue(src, field, pid));
    if (isStr(pid) && ID.test(pid) && versioned(src, field)) {
      delete e[field];                 // (an edit of every version, from before such edits were kept per version)
      var byVersion = isMap(e._v) ? e._v : {};
      var mine = isMap(byVersion[pid]) ? byVersion[pid] : {};
      if (none) delete mine[field];
      else mine[field] = copy(value);
      if (Object.keys(mine).length) byVersion[pid] = mine;
      else delete byVersion[pid];
      if (Object.keys(byVersion).length) e._v = byVersion;
      else delete e._v;
    } else if (none) delete e[field];
    else e[field] = copy(value);
    var keys = Object.keys(e).filter(function (k) { return k !== "_h"; });
    if (keys.length) {
      e._h = src.h;
      ds.edits[id] = e;
    } else delete ds.edits[id];
    return true;
  }
  /** Back to the deck's slide (its edits gone; an added slide is removed). */
  function resetSlide(ds, id) {
    var had = !!ds.edits[id];
    delete ds.edits[id];
    var n = ds.added.length;
    ds.added = ds.added.filter(function (a) { return a.id !== id; });
    if (ds.added.length !== n) {
      ds.hidden = ds.hidden.filter(function (x) { return x !== id; });
      ds.shown = ds.shown.filter(function (x) { return x !== id; });
      if (ds.order) ds.order = ds.order.filter(function (x) { return x !== id; });
      delete ds.checks[id];
      return true;
    }
    return had;
  }
  /** "Changed since you edited it": Use the new version (the edit goes) / Keep mine (the edit now counts as made
   *  on the new slide). */
  function dropEdit(ds, id) { delete ds.edits[id]; }
  function keepEdit(deck, ds, id) {
    var e = ds.edits[id];
    if (!e) return;
    (deck.slides || []).forEach(function (s) { if (s.id === id) e._h = s.h; });
  }
  var NEW_TEXT = {
    bullets: { title: "New slide", items: ["First point", "Second point"] },
    text: { title: "New slide", body: "Your text." },
    section: { title: "New part", number: "", subtitle: "" },
    qa: { title: "Questions", prompts: ["A question to get people talking"] },
  };
  /** A new slide of `layout` right after `afterId` → its id ("my-N"). Its first words are English placeholders,
   *  like the rest of the content. */
  function addSlide(deck, ds, layout, afterId) {
    if (ADD_LAYOUTS.indexOf(layout) < 0 || ds.added.length >= LIMITS.added) return "";
    var n = 1;
    ds.added.forEach(function (a) { var k = Number(a.id.slice(3)); if (k >= n) n = k + 1; });
    var id = "my-" + n;
    var s = copy(NEW_TEXT[layout]);
    s.id = id;
    s.layout = layout;
    s.notes = "";
    s.minutes = layout === "section" ? 0.25 : 1;
    s.after = slideId(afterId) ? afterId : "";
    ds.added.push(s);
    if (ds.order) {
      var at = ds.order.indexOf(afterId);
      if (at >= 0) ds.order.splice(at + 1, 0, id);
      else ds.order.push(id);
    }
    return id;
  }
  /** Turns a slide on or off in the presenter's version: the switch is only remembered when it differs from what
   *  the version does by itself. */
  function setShown(cur, id, on) {
    var ds = cur.ds;
    var e = cur.byId[id];
    if (!e || e.why === "facilitator" || e.why === "window") return false;
    ds.hidden = ds.hidden.filter(function (x) { return x !== id; });
    ds.shown = ds.shown.filter(function (x) { return x !== id; });
    var base = e.added ? true : inPreset(e.slide, cur.preset);
    if (on && !base) ds.shown.push(id);
    if (!on && base) ds.hidden.push(id);
    return true;
  }
  /** "Show all": every slide that can be in the show is on. */
  function showAll(cur) {
    cur.ds.hidden = [];
    cur.list.forEach(function (e) {
      if (e.why === "facilitator" || e.why === "window") return;
      var base = e.added ? true : inPreset(e.slide, cur.preset);
      if (!base && cur.ds.shown.indexOf(e.id) < 0) cur.ds.shown.push(e.id);
    });
  }
  /** Moves a slide `delta` places (or to index `to` when given) among ALL slides of the presenter's order. */
  function move(cur, id, delta, to) {
    var ids = cur.list.map(function (e) { return e.id; });
    var from = ids.indexOf(id);
    if (from < 0) return -1;
    var dest = isNum(to) ? to : from + delta;
    dest = Math.max(0, Math.min(ids.length - 1, dest));
    if (dest === from) return from;
    ids.splice(from, 1);
    ids.splice(dest, 0, id);
    cur.ds.order = ids;
    // an added slide moved by hand follows the order, not its anchor
    return dest;
  }
  /** "Original order": the deck's order again (the added slides at their places). */
  function originalOrder(ds) { ds.order = null; }

  /* ------------------------------------------------------------------ an updated deck */
  /** Was the stored state last fitted to a deck file built AFTER this one (`built`, ISO)? Another window (the
   *  presenter view, a second tab) has the newer file: this one must not prune what it does not know. */
  function newerSeen(ds, deck) {
    var a = ms(ds && ds.seen_built), b = ms(deck && deck.built);
    return isFinite(a) && isFinite(b) && a > b;
  }
  /** The stored version of a deck against the deck as it is now: drops what belongs to slides that are gone (and
   *  edited fields the slide's layout no longer has), keeps the rest by slide id. → { changed, stale: [ids], newer }.
   *  `changed` is about the presenter's version only: noting which deck file it now fits (seen, seen_built) is no
   *  change to store — else two windows with two deck files would keep rewriting it for each other. A state from a
   *  newer deck file (newerSeen) is not pruned at all: the caller fetches that file. */
  function reconcile(deck, ds) {
    var bySlide = Object.create(null);
    (deck.slides || []).forEach(function (s) { bySlide[s.id] = s; });
    var addedIds = Object.create(null);
    ds.added.forEach(function (a) { addedIds[a.id] = 1; });
    var known = function (id) { return !!bySlide[id] || !!addedIds[id]; };
    var mine = function () { var x = copy(ds); delete x.seen; delete x.seen_built; return JSON.stringify(x); };
    if (newerSeen(ds, deck)) {
      var keepStale = Object.keys(ds.edits).filter(function (id) { return bySlide[id] && isStr(ds.edits[id]._h) && ds.edits[id]._h !== bySlide[id].h; });
      return { changed: false, stale: keepStale, newer: true };
    }
    var before = mine();
    ds.hidden = ds.hidden.filter(known);
    ds.shown = ds.shown.filter(known);
    if (ds.order) {
      ds.order = ds.order.filter(known);
      if (!ds.order.length) ds.order = null;
    }
    Object.keys(ds.edits).forEach(function (id) {
      var s = bySlide[id];
      if (!s) { delete ds.edits[id]; return; }
      var e = ds.edits[id];
      Object.keys(e).forEach(function (k) { if (k !== "_h" && k !== "_v" && !kindOf(s.layout, k)) delete e[k]; });
      // one version's edits: of a version the deck still has, and of fields the slide's layout still has
      if (isMap(e._v)) {
        Object.keys(e._v).forEach(function (pid) {
          var m = e._v[pid];
          var known = !Array.isArray(deck.presets) || deck.presets.some(function (p) { return p && p.id === pid; });
          if (known && isMap(m)) Object.keys(m).forEach(function (k) { if (!kindOf(s.layout, k)) delete m[k]; });
          if (!known || !isMap(m) || !Object.keys(m).length) delete e._v[pid];
        });
        if (!Object.keys(e._v).length) delete e._v;
      }
      if (!Object.keys(e).filter(function (k) { return k !== "_h"; }).length) delete ds.edits[id];
    });
    Object.keys(ds.checks).forEach(function (id) { if (!known(id)) delete ds.checks[id]; });
    if (deck.presets && ds.preset && !deck.presets.some(function (p) { return p.id === ds.preset; })) ds.preset = "";
    var stale = Object.keys(ds.edits).filter(function (id) { return isStr(ds.edits[id]._h) && ds.edits[id]._h !== bySlide[id].h; });
    if (isStr(deck.version)) ds.seen = deck.version;
    if (isStr(deck.built) && deck.built.length <= 40) ds.seen_built = deck.built;
    return { changed: mine() !== before, stale: stale, newer: false };
  }

  /* ------------------------------------------------------------------ the "my version" file */
  function sharedKeys(deck) {
    return ((deck && deck.fillins) || []).filter(function (f) { return f && f.shared; }).map(function (f) { return f.key; });
  }
  /** The presenter's version of one deck, as the file "Save my version" downloads. */
  function exportVersion(deck, state, nowIso) {
    var ds = normDeck(state && state.decks && state.decks[deck.id]);
    var shared = {};
    var sf = (state && state.shared && state.shared.fill) || {};
    sharedKeys(deck).forEach(function (k) { if (has(sf, k)) shared[k] = sf[k]; });
    return {
      app: FILE_APP, v: SCHEMA, deck: deck.id, deck_title: String(deck.title || ""), deck_version: String(deck.version || ""),
      exported: nowIso || new Date().toISOString(),
      preset: ds.preset, hidden: ds.hidden, shown: ds.shown, order: ds.order, edits: ds.edits, added: ds.added,
      fill: ds.fill, shared: shared, checks: ds.checks,
    };
  }
  var FILE_KEYS = ["app", "v", "deck", "deck_title", "deck_version", "exported", "preset", "hidden", "shown", "order", "edits", "added", "fill", "shared", "checks"];
  /**
   * A "my version" file (its text, or the parsed value) for `deck` → { ok, data, errors: [{ key, detail }] }.
   * Strict: the right app, schema and deck; only the known keys; ids, layouts and fields that exist; every text a
   * string within its size and without HTML. Edits of slides the deck no longer has are left out (as when the deck
   * changes); everything else wrong refuses the file — nothing of it is applied.
   */
  function validateImport(input, deck) {
    STRICT = true;
    try { return checkFile(input, deck); } finally { STRICT = false; }
  }
  function checkFile(input, deck) {
    var errors = [];
    function err(key, detail) { errors.push({ key: key, detail: detail === undefined ? "" : String(detail) }); }
    var raw = input;
    if (isStr(input)) {
      if (input.length > LIMITS.fileBytes) { err("pres.err.too_big"); return { ok: false, errors: errors }; }
      try { raw = JSON.parse(input.replace(/^﻿/, "")); } catch (e) { err("pres.err.not_json"); return { ok: false, errors: errors }; }
    }
    if (!isMap(raw) || raw.app !== FILE_APP) { err("pres.err.not_ours"); return { ok: false, errors: errors }; }
    if (raw.v !== SCHEMA) { err("pres.err.newer", raw.v); return { ok: false, errors: errors }; }
    if (!deck || raw.deck !== deck.id) { err("pres.err.other_deck", isStr(raw.deck_title) ? raw.deck_title.slice(0, 120) : raw.deck); return { ok: false, errors: errors }; }
    Object.keys(raw).forEach(function (k) { if (FILE_KEYS.indexOf(k) < 0) err("pres.err.unknown", k); });
    var bySlide = {};
    (deck.slides || []).forEach(function (s) { bySlide[s.id] = s; });
    var ds = emptyDeck();
    if (has(raw, "preset")) {
      if (!isStr(raw.preset) || (raw.preset && !ID.test(raw.preset))) err("pres.err.bad_field", "preset");
      else ds.preset = (deck.presets || []).some(function (p) { return p.id === raw.preset; }) ? raw.preset : "";
    }
    ["hidden", "shown"].forEach(function (k) {
      if (!has(raw, k)) return;
      if (!Array.isArray(raw[k]) || raw[k].length > LIMITS.ids || !raw[k].every(slideId)) err("pres.err.bad_field", k);
      else ds[k] = uniq(raw[k]);
    });
    if (has(raw, "order") && raw.order !== null) {
      if (!Array.isArray(raw.order) || raw.order.length > LIMITS.ids || !raw.order.every(slideId)) err("pres.err.bad_field", "order");
      else ds.order = uniq(raw.order);
    }
    var addedIds = {};
    if (has(raw, "added")) {
      if (!Array.isArray(raw.added) || raw.added.length > LIMITS.added) err("pres.err.bad_field", "added");
      else {
        raw.added.forEach(function (a, i) {
          var c = cleanAdded(a);
          if (!c.ok) {
            if (isMap(a) && JSON.stringify(a).match(HTML)) err("pres.err.html", "added[" + i + "]");
            else err("pres.err.bad_added", (isMap(a) && isStr(a.id) ? a.id : "#" + (i + 1)) + (c.field ? " · " + c.field : ""));
          } else if (addedIds[c.slide.id]) err("pres.err.bad_added", c.slide.id);
          else { addedIds[c.slide.id] = 1; ds.added.push(c.slide); }
        });
      }
    }
    if (has(raw, "edits")) {
      if (!isMap(raw.edits) || Object.keys(raw.edits).length > LIMITS.ids) err("pres.err.bad_field", "edits");
      else {
        Object.keys(raw.edits).forEach(function (id) {
          if (!slideId(id)) { err("pres.err.bad_field", "edits." + id.slice(0, 40)); return; }
          var s = bySlide[id];
          if (!s) return;                       // a slide the deck no longer has: left out, as reconcile does
          var e = cleanEdit(raw.edits[id], s.layout);
          if (!e.ok) err(e.error, id + (e.field ? " · " + e.field : ""));
          else if (Object.keys(e.edit).filter(function (k) { return k !== "_h"; }).length) ds.edits[id] = e.edit;
        });
      }
    }
    ["fill", "shared"].forEach(function (k) {
      if (!has(raw, k)) return;
      var m = raw[k];
      if (!isMap(m) || Object.keys(m).length > LIMITS.fill) { err("pres.err.bad_field", k); return; }
      Object.keys(m).forEach(function (key) {
        var v = m[key];
        if (!KEY.test(key) || !isStr(v) || v.length > LIMITS.fillText) err("pres.err.bad_field", k + "." + key.slice(0, 40));
        else if (HTML.test(v)) err("pres.err.html", k + "." + key);
      });
    });
    if (has(raw, "checks")) {
      if (!isMap(raw.checks)) err("pres.err.bad_field", "checks");
      else {
        Object.keys(raw.checks).forEach(function (id) {
          var v = raw.checks[id];
          if (!slideId(id) || !Array.isArray(v) || v.length > LIMITS.checks || !v.every(function (x) { return isStr(x) && CHECK.test(x); })) err("pres.err.bad_field", "checks");
          else if (bySlide[id] || addedIds[id]) ds.checks[id] = uniq(v);
        });
      }
    }
    if (errors.length) return { ok: false, errors: errors };
    ds.fill = cleanFill(raw.fill);
    var shared = cleanFill(raw.shared);
    var keys = sharedKeys(deck);
    Object.keys(shared).forEach(function (k) { if (keys.indexOf(k) < 0) delete shared[k]; });
    reconcile(deck, ds);
    return { ok: true, errors: [], data: { deck: ds, shared: shared, title: isStr(raw.deck_title) ? raw.deck_title : "", exported: isStr(raw.exported) ? raw.exported : "" } };
  }
  /** Puts an imported version in place of the deck's (→ the previous one, for Undo). */
  function importVersion(state, deck, data) {
    var before = { deck: copy(state.decks[deck.id] || null), shared: copy(state.shared.fill) };
    var ds = copy(data.deck);
    ds.seen = deck.version || "";
    ds.seen_built = isStr(deck.built) ? deck.built : "";
    ds.updated = new Date().toISOString();
    state.decks[deck.id] = ds;
    Object.keys(data.shared || {}).forEach(function (k) { state.shared.fill[k] = data.shared[k]; });
    return before;
  }

  /* ------------------------------------------------------------------ reset (with Undo) */
  /** "Reset this presentation": the deck's part goes (shared blanks stay). → what it was, for Undo. */
  function resetDeck(state, id) {
    var before = state.decks[id] ? copy(state.decks[id]) : null;
    delete state.decks[id];
    return before;
  }
  function restoreDeck(state, id, before) {
    if (before) state.decks[id] = normDeck(before);
    else delete state.decks[id];
  }
  /** "Reset all four": everything, the shared blanks too. → the whole previous state, for Undo. */
  function resetAll(state) {
    var before = copy(state);
    state.decks = {};
    state.shared = { fill: {} };
    return before;
  }

  /* ------------------------------------------------------------------ the module */
  root.GVP = {
    VERSION: VERSION, SCHEMA: SCHEMA, STORAGE_KEY: STORAGE_KEY, FILE_APP: FILE_APP, LAYOUTS: LAYOUTS, ADD_LAYOUTS: ADD_LAYOUTS,
    ACCENTS: ACCENTS, PRINT_MODES: PRINT_MODES, LIMITS: LIMITS, EN: EN, LAYOUT_FIELDS: LAYOUT_FIELDS, ID: ID, MY_ID: MY_ID,
    // facts of the day
    liveText: liveText, liveValues: liveValues, noticeOn: noticeOn, inWindow: inWindow, liveRows: liveRows, LIMIT: LIMIT,
    // the stored state
    emptyState: emptyState, emptyDeck: emptyDeck, normState: normState, normDeck: normDeck, deckState: deckState,
    summary: summary, sharedCount: sharedCount,
    // the current version, the clock
    presetOf: presetOf, inPreset: inPreset, orderOf: orderOf, current: current, inVersion: inVersion,
    versioned: versioned, versionValue: versionValue, minutesOf: minutesOf, schedule: schedule,
    clock: clock, aboutText: aboutText, timeLine: timeLine, slideRef: slideRef, agendaRows: agendaRows,
    agendaUnchanged: agendaUnchanged,
    // blanks
    fillDefs: fillDefs, fillValue: fillValue, fillsIn: fillsIn, fillGroups: fillGroups, emptyBlanks: emptyBlanks,
    // text
    subst: subst, inline: inline, rich: rich, plain: plain, safeHref: safeHref, showUrl: showUrl, noteLines: noteLines,
    fmt: fmt, BLANK_OPEN: BLANK_OPEN, BLANK_CLOSE: BLANK_CLOSE,
    // editing
    fieldsOf: fieldsOf, kindOf: kindOf, toText: toText, fromText: fromText, setField: setField, resetSlide: resetSlide,
    dropEdit: dropEdit, keepEdit: keepEdit, addSlide: addSlide, setShown: setShown, showAll: showAll, move: move,
    originalOrder: originalOrder, cleanEdit: cleanEdit, cleanAdded: cleanAdded,
    // an updated deck, files, reset
    reconcile: reconcile, newerSeen: newerSeen, exportVersion: exportVersion, validateImport: validateImport, importVersion: importVersion,
    resetDeck: resetDeck, restoreDeck: restoreDeck, resetAll: resetAll,
  };
})(typeof window !== "undefined" ? window : globalThis);
