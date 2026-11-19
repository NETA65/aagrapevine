/* The Grapevine & La Viña Bingo cards' logic (the GVR / RLV corner → /gvr/bingo/: bingo cards a GVR or RLV prints and
   takes to a group, a district meeting, an assembly, a workshop or our table, to get people meeting, reading and
   talking). The builder itself — the settings form, the live preview, printing — is src/assets/js/bingo.js (Alpine
   `bingoBuilder`); the squares are content/bingo/bingo.csv (content/bingo/README.md: the owner's guide to every
   column), read and checked at build by eleventy/filters/bingo.js (the `bingo` global, src/_data/bingo.js) and
   embedded in the page (<script type="application/json" id="bingo-data">). The build runs this very file once in
   Node (eleventy/filters/bingo-sample.js bingoCore(), in a vm context, as booth-core.js runs for the booth's
   question of the day) for the page's no-JS sample card and the /gvr/ teaser's mini card: the squares the browser
   would draw with the same settings.
   Pure functions, no DOM, no fetch, no storage, no clock: the date comes in the settings, and newCode takes its
   random numbers as an argument. Tested in Node by tests/test_r34_bingo.py. A plain script (no imports; no optional
   chaining or ??: an older phone must run it): it defines window.GVBingo (globalThis.GVBingo in Node).

   THE SQUARES — bingo.items (eleventy/filters/bingo.js loadBingo: checked, `on`, every placeholder filled but
   {event}): [{ id, type, pub, cat, where: [...], pin, weight, from, until, text: { en, es }, short: { en, es },
   label: { en, es } }]. A language without words is "" (the square is not offered in it); label "" = the type's
   own (WORDS.label). type — and the MARK the card draws in the square (MARKS):
     check (do it, cross it off: a small tick circle, "tick") · name (find someone: a "Name & group" line, "line") ·
     phone (trade numbers: "Name & phone", "line") · write (write an answer: a line labelled by label_*, "line") ·
     sign (someone initials it: a small box, "box") · info (an information square — the meetings, how to reach us:
     nothing to write, a tinted look with an icon, "icon"; crossed off like any other). The FREE square: "free".
   pub: gv | lv | both (the magazine filter, the square's accent colour) · cat: one of CATS (a new one in the CSV
   works here as it is) · where: the occasions it fits (WHERES without "any"; [] = everywhere) · pin: "Always on
   every card" by default · weight: 0.5–5 (how often it is drawn beside the others; anything else counts as 1) ·
   from / until: "YYYY-MM-DD" or "" / null (the event's date must be inside, both days included).

   THE SETTINGS — GVBingo.DEFAULTS; normalize(raw, base) makes anything safe to use: unknown keys dropped, a wrong
   type or an unknown word replaced by the base's value (base: a partial set put on DEFAULTS first — the /es/ page's
   { lang: "es" }), every number rounded and clamped; it never throws, whatever is in storage or the address.
     title ("" = WORDS.title: "Grapevine & La Viña Bingo" in the card's language; ≤ 60) · event (the "Event name",
     {event} in the squares; ≤ 60) · date ("YYYY-MM-DD", 2000–2099: the event's day, for from / until; "" = no day:
     the rows with a from or an until are left out — the page always sets one, today in Central time by default) ·
     lang (the CARD's language: en | es, chosen apart from the page's) · pub (both | gv | lv: gv offers gv + both, lv
     offers lv + both) · rows, cols (3–10 each; rectangular grids too) · free (the "Free square in the middle"
     switch, kept as set: the card has one only when rows and cols are both odd — freeOn(s)) · freeText (its words;
     "" = WORDS.free, "FREE" / "LIBRE"; ≤ 16) · where (any | group | district | assembly | acm | workshop | booth |
     committee | online) · cats ({ <cat>: false }: only the categories switched OFF; any other is on) · infoMax
     (0–4, 3 by default: that many info squares on each card — fewer when the pool has fewer —, the pinned ones
     first: a hard cap, pinned info squares included, so "0" means none, whatever is pinned) · pick
     ({ <id>: 1 | 0 }: the squares the GVR took in (1) or left out (0) by hand, against what the filters say) · pin
     ({ <id>: 1 | 0 }: "always on every card" set (1) or unset (0) against the row's own pin) · count (cards: 1–60)
     · same (true: every card the same as card 1) · code (the game code: 4–6 of ALPHABET — A–Z without I and O,
     2–9; lowercase is read as uppercase; "" until the page draws one: newCode) · perSheet (1 | 2 | 4 cards on a
     sheet, kept as set: 2 only when rows and cols are ≤ 5, 4 only when ≤ 4 — perSheetOf(s) is the number used) ·
     paper (letter | a4) · orient (portrait | landscape) · color (false = black and white, the ink saver) · showName
     (Name & group lines at the top) · showRules ("How to play") · rules (its words; "" = the page's own; ≤ 320,
     line breaks kept) · showInfo (the "Meetings & contact" strip).
   The same code and settings give the same cards, on any device: what "Copy a link to these settings" relies on.

   THE POOL — pool(items, s) → { pool, pinned, info, rest, cells, need, have, infoTake, free, ok }: the squares a
   card may have. why(item, s) says why one may not (null when it may), checked in this order:
     bad (not a square: no id, an unknown type) · lang (no words in the card's language) · date (outside from /
     until, or no date) — these two are the "hard" ones: offered(item, s) is false and the builder does not list it
     · off (left out by hand: pick 0) · then a square taken in by hand (pick 1, or pin 1) is in, whatever the rest
     says · pub (the magazine) · where (the occasion: "any", or the row's where empty or naming it) · cat (its
     category is off).
   pinned: the pool's squares pinned (the row's pin unless pin[id] is 0, or pin[id] 1; info ones too) · info: the
   pool's info squares (pinned or not) · rest: the others (neither pinned nor info) · cells = rows × cols · need =
   cells − the FREE square · infoTake = how many info squares a card gets (min(infoMax, info.length)) · have = the
   pinned squares that are not info + infoTake + rest — what a card can be filled from · ok = have ≥ need (else the
   page says "choose a smaller grid or more categories" and Print waits). A row twice (the same id) counts once: the
   first that may be on the card (the CSV checker refuses a second id anyway).
   catCounts(items, s) → { <cat>: n } the squares of each category the card could have with that category on (the
   chips' counts) · setPick(s, item, on) / setPin(s, item, on) → new settings with that square taken in / left out,
   pinned / unpinned (the map keeps only what differs from the row's own state, so the link stays short) ·
   pickRows(items, s) → the builder's "Choose squares yourself" list: [{ item, on, pin }] for every square offered,
   in the items' order — on: it may be on the card (why is null); pin: "always" ticked, only for a square that is on
   (one left out shows "always" off, whatever pins it). One normalize for the whole list, not one per row.

   THE CARD — card(items, s, index, words, opts) → { index, code, lang, rows, cols, dense, free, cells } or, when the
   pool is too small, { error: "short", have, need }. index counts from 0 ("Card 1 of 10" is index 0). Each square's
   draw is seeded by the code and the card ("<code>:<index>", card 0's for every card when s.same): the same code and
   settings give the same card, and a row added to the CSV changes only the cards where it wins a place (one square
   swapped; the squares of those cards are shuffled again).
     1. the pinned squares that are not info first (more of them than the card's places: the draw below picks
        among them)
     2. then infoTake info squares: the pinned ones first (more of them than infoTake: drawn among them), then the
        others, each group by the draw below
     3. then the rest: a weighted draw without replacement (Efraimidis–Spirakis: each square's key u^(1/weight),
        u from mulberry32 over "<code>:<index>:<id>"; the highest keys win) — never a square twice on a card
     4. the places shuffled (Fisher–Yates, mulberry32 over "<code>:<index>"), the FREE square in the very middle
   cells (row by row, rows × cols of them): { id, free, type, cat, pub, pin, mark, text, label } — the FREE square
   { id: "free", free: true, type: "free", mark: "free", text: freeText or WORDS.free }. A big grid (rows or cols
   ≥ 7) takes the squares' short words where they have them, and so does a card whose squares come out smaller than
   SMALL_CELL (1.2 in) on its sheet — a 5×5 two on a sheet, a 4×4 four on a sheet, a 6×6: dense (90 characters do not
   fit a ¾-inch square above 6 pt). The page measures the squares it draws and says which (opts.dense: true / false);
   without it — Node, the build's sample cards — denseOf(s) works it out from cardPlan's estimate. {event} becomes
   s.event, or words.thisEvent ("this event" / "este evento") when it is empty. label: the row's own, or
   words.label[type] (name, phone, write, sign; "" for check and info). words: the card's words in ITS language (the
   page's src/_i18n/bingo.json card words; anything missing comes from WORDS[s.lang]).
   cards(items, s, words, opts) → s.count cards (all of them card 0's squares when s.same, each with its own index),
   or the { error: "short" } above. poolCells(items, s, words, opts) → every square the pool may put on a card, as
   card() would draw it (its cells' shape, no FREE square), once each in the items' order — by steps 1–3: the info
   squares only while a card gets some (infoTake), only the pinned ones when they fill that share, the rest only while
   places are left for them —, [] when the pool is too small: what the page measures to keep every card of a run at
   6 pt or more (bingo.js placeCard).

   THE LINK — encode(s) → "#grid=5x5&code=K7Q2&lang=en&…": the grid, the code and the card's language always, then
   only what differs from DEFAULTS (text URI-encoded; id and category lists joined with "."): grid (5x5, rows x
   cols) code cards same lang mag (pub) where title event date free freetext off (the categories off) info (infoMax)
   in / out (pick 1 / 0) pin / unpin (pin 1 / 0) per (perSheet) paper orient bw (1 = black and white) names
   (showName) howto (showRules) rules strip (showInfo); a switch is 1 / 0. decode(hash) → the part of the settings the
   address holds: every key on its own, strictly — a garbled, unknown or out-of-range value is skipped (nothing
   clamped), and it never throws. fromHash(hash, base) → the whole settings of a link (normalize(decode(hash),
   base): a link is a full setup, applied on the defaults — never on what this device remembers), or null when the
   address holds no bingo setting at all (#main and the like). decode(encode(s)) gives normalize(s) back.

   THE SHEET — sheetPlan(s) → the printed page, in inches: { paper, orient, size ("letter portrait" | "A4
   landscape" …, for @page), page: { w, h } (Letter 8.5 × 11, A4 8.27 × 11.69, turned for landscape), margin,
   area: { w, h } (inside the margins), gap, perSheet, across, down, slots: [{ x, y, w, h }] (each card's place,
   from the area's top left corner, row by row), count, sheets }: 2 on a sheet side by side on a wide page, one
   above the other on a tall one; 4 two by two; a dashed cut line can go in the middle of each gap.
   cardPlan(s, slot) → an estimate of one card in its slot, made the way bingo.css draws it (the card's padding and
   border, the grid's lines; the parts' heights measured in Chrome on a Letter card and scaled): { layout ("stack":
   head, name lines, grid, then how to play beside the meetings strip, the small print, one under the other |
   "side": on a wide card — landscape, two on a portrait sheet — the grid the whole height on the left, the head,
   the name lines, how to play and the meetings strip in a column of side.w on its right, the small print under
   both; chosen when its squares come out 5 % bigger and the column fits), w, h, scale (the parts' size against a
   whole Letter card, 0.6–1), header, names, rules, info, qr, foot, gap, side: { w, h } (the side column; 0 × 0 in
   "stack"), grid: { w, h }, cell } (inches; names / rules / info are 0 when they are off) — the page measures and
   fits the real thing (bingo.js chooseLayout, which also has "top": the head across the top, for a column too
   crowded); the no-JS sample card, which cannot measure, uses these, and denseOf. The estimate is close (within
   about 5 %) for one card on a sheet; for 2 or 4 on a sheet it can be 15 % off (the meetings strip's longer lines
   are not in it), and only the page, which measures, decides those cards' layout and short words.
   layout(s) → { sheet, card }. SIDE: the side column's narrowest (inches, × the scale).
   fontGuess(text, cellInches, mark) → a starting font size in pt (MIN_PT–MAX_PT, in steps of 0.5) for a square's
   words to fit its square above its mark (mark: one of MARKS' values; true = "line", false = "tick"): a word wrap
   with estimated letter widths, hyphenation allowed only at 8 pt and below; an e-mail may break after its "@", the
   site's address after "/" and before ".", as the page lets them (bingo.js breakable, the sample's <wbr>:
   eleventy/filters/bingo-sample.js bingoBreaks). (Its top
   size, 0.17 × the square, is below the one bingo.js starts its measuring from, 0.19 ×: a guess that cannot
   measure stays on the safe side.)
   headPieces(text) → a typed title or event in pieces (their join is the text), a line free to break between two:
   inside a piece of 12 characters or more with no space (a pasted link, an e-mail, a hashtag), after a "/", ".", "@",
   "-" or "_" and between a small letter and a capital — bingo.js puts a <wbr> there (headIn), so a long piece breaks
   there rather than widen the head's column past the 6 pt floor (chooseLayout); a piece with none breaks anywhere
   (bingo.css overflow-wrap) rather than stick out.

   THE REST — rng(seed) → mulberry32, a function giving numbers in [0, 1) (seed: a number, or a word through
   seedOf, FNV-1a) · newCode(rand, length) → a new game code (length 4–6, default 4; rand: a function like
   Math.random, which it uses when given none) · cleanCode(v) → the code, uppercase, or "" · freeOn(s), needOf(s),
   perSheetOf(s), perSheetChoices(s) ([1], [1, 2] or [1, 2, 4]) · fillEvent(text, event, words) · wordsFor(lang,
   words) → the card words with every field there. */
(function (root) {
  "use strict";

  var VERSION = "1.0.0";
  var LANGS = ["en", "es"];
  var PUBS = ["both", "gv", "lv"];
  // the occasions (the CSV's `where`, the builder's "Where are you taking it?"); "any" = every square. The same list
  // as eleventy/filters/bingo.js: a new occasion goes in both (and in src/_i18n/bingo.json)
  var WHERES = ["any", "group", "district", "assembly", "acm", "workshop", "booth", "committee", "online"];
  // the categories in the builder's order (the CSV's `cat`); a category the CSV adds works here without a change
  var CATS = ["people", "read", "write", "listen", "service", "meetings", "history", "fun"];
  // what each type draws in its square, under its words
  var MARKS = { check: "tick", name: "line", phone: "line", write: "line", sign: "box", info: "icon", free: "free" };
  // the types whose line or box has a label (the row's label_*, else WORDS.label)
  var LABELLED = ["name", "phone", "write", "sign"];
  var PAPERS = { letter: { w: 8.5, h: 11 }, a4: { w: 8.27, h: 11.69 } };
  var ORIENTS = ["portrait", "landscape"];
  var PER_SHEET = [1, 2, 4];
  // every number of the settings: [lowest, highest]
  var LIMITS = { rows: [3, 10], cols: [3, 10], count: [1, 60], infoMax: [0, 4] };
  var TEXT_MAX = { title: 60, event: 60, freeText: 16, rules: 320 };
  // a grid this big on either side takes the squares' short words — and so does a card whose squares come out
  // smaller than SMALL_CELL inches on paper (two or four on a sheet, a 6×6: the page measures them, THE CARD)
  var DENSE = 7, SMALL_CELL = 1.2;
  // the game code's letters: no I or O, no 0 or 1 (read aloud and typed back without a mix-up)
  var ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  var CODE = /^[A-HJ-NP-Z2-9]{4,6}$/;
  var ID = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
  var ID_MAX = 48;
  var CAT_ID = /^[a-z][a-z0-9-]{0,31}$/;
  var DAY = /^(\d{4})-(\d{2})-(\d{2})$/;
  // the most ids a pick or pin map keeps (the CSV has a few hundred rows)
  var PICK_MAX = 1000;
  var HASH_MAX = 30000;
  // the printed sheet (inches): the margin all round, the space between two cards on one sheet
  var MARGIN = 0.4, GAP = 0.4;
  // a square's words: never smaller, never bigger (pt)
  var MIN_PT = 6, MAX_PT = 20;

  /* The words a card itself needs, in both languages (a card's language is chosen apart from the page's). The page
     passes its own — src/_i18n/bingo.json's card words, the one place to change them — to card() / cards(); these
     are the same words, for Node, the tests and anything the page leaves out. */
  var WORDS = {
    en: {
      title: "Grapevine & La Viña Bingo",
      free: "FREE",
      thisEvent: "this event",
      label: { name: "Name & group", phone: "Name & phone", write: "Answer", sign: "Initials" },
    },
    es: {
      // La Viña first on a Spanish text that names both
      title: "Bingo de La Viña y Grapevine",
      free: "LIBRE",
      thisEvent: "este evento",
      label: { name: "Nombre/grupo", phone: "Nombre y tel.", write: "Respuesta", sign: "Iniciales" },
    },
  };

  // (infoMax 3: the shipped CSV pins three information squares — our Grapevine Meeting, the committee meeting, how to
  // write to us — "always on every card", and the cap counts them, so a lower default would leave one out of every card)
  var DEF = {
    title: "", event: "", date: "", lang: "en", pub: "both",
    rows: 5, cols: 5, free: true, freeText: "",
    where: "any", cats: {}, infoMax: 3, pick: {}, pin: {},
    count: 10, same: false, code: "",
    perSheet: 1, paper: "letter", orient: "portrait", color: true,
    showName: true, showRules: true, rules: "", showInfo: true,
  };
  var BOOLS = ["free", "same", "color", "showName", "showRules", "showInfo"];
  var ENUMS = { lang: LANGS, pub: PUBS, where: WHERES, paper: ["letter", "a4"], orient: ORIENTS };

  /* ------------------------------------------------------------------ small helpers */
  function isMap(v) { return !!v && typeof v === "object" && !Array.isArray(v); }
  function isStr(v) { return typeof v === "string"; }
  function isNum(v) { return typeof v === "number" && isFinite(v); }
  function has(o, k) { return isMap(o) && Object.prototype.hasOwnProperty.call(o, k); }
  function copy(v) { return v === undefined ? undefined : JSON.parse(JSON.stringify(v)); }
  function clamp(n, lo, hi) { return n < lo ? lo : n > hi ? hi : n; }
  function str(v) { return isStr(v) ? v : isNum(v) ? String(v) : ""; }
  function list(v) { return Array.isArray(v) ? v : []; }
  function r3(n) { return Math.round(n * 1000) / 1000; }
  /** A number from a number or a numeric string ("12", " 4 "); NaN for anything else. */
  function num(v) {
    if (isNum(v)) return v;
    if (isStr(v) && /^\s*-?\d+(?:\.\d+)?\s*$/.test(v)) return parseFloat(v);
    return NaN;
  }
  /** A switch's value: true / false (also "true" / "false", "1" / "0", 1 / 0); `dflt` for anything else. */
  function bool(v, dflt) {
    if (v === true || v === 1 || v === "true" || v === "1") return true;
    if (v === false || v === 0 || v === "false" || v === "0") return false;
    return dflt;
  }
  /** Text typed in the builder, kept as typed (no trimming while someone types): control characters become a
   *  space (line breaks too, unless `lines`), cut at max. */
  function line(v, max, lines) {
    var s = lines ? String(v).replace(/\r\n?/g, "\n").replace(/[\u0000-\u0009\u000b-\u001f\u007f]+/g, " ")
                  : String(v).replace(/[\u0000-\u001f\u007f]+/g, " ");
    return wellFormed(s.slice(0, max));
  }
  /** Without a half of a surrogate pair (one cut at the end, or pasted alone): encodeURIComponent throws on one. */
  function wellFormed(s) {
    var out = "";
    for (var i = 0; i < s.length; i++) {
      var c = s.charCodeAt(i);
      if (c >= 0xd800 && c <= 0xdbff) {
        var d = i + 1 < s.length ? s.charCodeAt(i + 1) : 0;
        if (d >= 0xdc00 && d <= 0xdfff) { out += s.charAt(i) + s.charAt(i + 1); i++; }
      } else if (c < 0xdc00 || c > 0xdfff) out += s.charAt(i);
    }
    return out;
  }
  /** "YYYY-MM-DD" of a real day of 2000–2099, else "". */
  function day(v) {
    var m = isStr(v) ? DAY.exec(v.trim()) : null;
    if (!m) return "";
    var y = +m[1], mo = +m[2], d = +m[3];
    if (y < 2000 || y > 2099 || mo < 1 || mo > 12 || d < 1) return "";
    var last = new Date(Date.UTC(y, mo, 0)).getUTCDate();
    return d <= last ? m[0] : "";
  }
  function validId(v) { return isStr(v) && v.length <= ID_MAX && ID.test(v); }
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

  /* ------------------------------------------------------------------ the settings */
  /** The game code as typed, uppercase, spaces and dashes out — or "" when it is not one (4–6 of ALPHABET). */
  function cleanCode(v) {
    var c = isStr(v) ? v.replace(/[\s-]+/g, "").toUpperCase() : "";
    return CODE.test(c) ? c : "";
  }
  /** A new game code: `length` (4–6, default 4) of ALPHABET, from rand (a function giving [0, 1); Math.random when
   *  none is given). */
  function newCode(rand, length) {
    var r = typeof rand === "function" ? rand : Math.random;
    var n = clamp(Math.round(isNum(length) ? length : 4), 4, 6);
    var out = "";
    for (var i = 0; i < n; i++) {
      var x = Number(r());
      var k = Math.floor((isFinite(x) ? Math.abs(x) % 1 : 0) * ALPHABET.length);
      out += ALPHABET.charAt(k);
    }
    return out;
  }
  /** { <cat>: false } from a map ({ fun: false, read: true } → { fun: false }) or a list of the categories off. */
  function catsOf(v) {
    var out = {};
    if (Array.isArray(v)) {
      v.forEach(function (c) { if (isStr(c) && CAT_ID.test(c)) out[c] = false; });
    } else if (isMap(v)) {
      Object.keys(v).forEach(function (c) { if (CAT_ID.test(c) && bool(v[c], true) === false) out[c] = false; });
    }
    return out;
  }
  /** { <id>: 1 | 0 } from a map (1 / true / "1" → 1, 0 / false / "0" → 0; anything else dropped). */
  function flagsOf(v) {
    var out = {}, n = 0;
    if (!isMap(v)) return out;
    Object.keys(v).forEach(function (id) {
      if (n >= PICK_MAX || !validId(id)) return;
      var b = bool(v[id], null);
      if (b === null) return;
      out[id] = b ? 1 : 0;
      n++;
    });
    return out;
  }
  /** One key of the settings: raw's value made safe, or the base's. */
  function normKey(k, v, b) {
    if (v === undefined) return b;
    if (BOOLS.indexOf(k) >= 0) return bool(v, b);
    if (has(ENUMS, k)) return ENUMS[k].indexOf(v) >= 0 ? v : b;
    if (has(LIMITS, k)) {
      var n = num(v);
      return isNaN(n) ? b : clamp(Math.round(n), LIMITS[k][0], LIMITS[k][1]);
    }
    if (has(TEXT_MAX, k)) return isStr(v) || isNum(v) ? line(v, TEXT_MAX[k], k === "rules") : b;
    switch (k) {
      case "date": return v === "" ? "" : day(v) || b;
      case "code": return v === "" ? "" : cleanCode(v) || b;
      case "perSheet": return PER_SHEET.indexOf(num(v)) >= 0 ? num(v) : b;
      case "cats": return isMap(v) || Array.isArray(v) ? catsOf(v) : b;
      case "pick": case "pin": return isMap(v) ? flagsOf(v) : b;
    }
    return b;
  }
  /** Settings safe to use: raw on top of base (a partial set: the page's { lang: "es" }) on top of DEFAULTS. Never
   *  throws; returns a new object. */
  function normalize(raw, base) {
    var b = copy(DEF);
    if (isMap(base)) Object.keys(DEF).forEach(function (k) { b[k] = normKey(k, base[k], b[k]); });
    var r = isMap(raw) ? raw : {};
    var out = {};
    Object.keys(DEF).forEach(function (k) { out[k] = normKey(k, r[k], b[k]); });
    return out;
  }
  /** A FREE square in the middle: the switch on, and rows and cols both odd. */
  function freeOn(s) { return !!s.free && s.rows % 2 === 1 && s.cols % 2 === 1; }
  /** The squares a card needs (its places but the FREE one). */
  function needOf(s) { return s.rows * s.cols - (freeOn(s) ? 1 : 0); }
  /** The cards on a sheet the grid allows: [1], [1, 2] (rows and cols ≤ 5) or [1, 2, 4] (≤ 4). */
  function perSheetChoices(s) {
    var big = Math.max(s.rows, s.cols);
    return big <= 4 ? [1, 2, 4] : big <= 5 ? [1, 2] : [1];
  }
  /** The cards on a sheet: perSheet when the grid allows it, else the most it allows. */
  function perSheetOf(s) {
    var c = perSheetChoices(s), want = PER_SHEET.indexOf(s.perSheet) >= 0 ? s.perSheet : 1;
    return c.indexOf(want) >= 0 ? want : c[c.length - 1];
  }

  /* ------------------------------------------------------------------ the pool */
  function textIn(item, lang) { return isMap(item.text) ? str(item.text[lang]).trim() : ""; }
  function isInfo(item) { return item.type === "info"; }
  function notInfo(item) { return item.type !== "info"; }
  function weightOf(item) {
    var w = num(item.weight);
    return isNaN(w) || w < 0.5 || w > 5 ? 1 : w;
  }
  function wheresOf(item) { return list(item.where).filter(isStr); }
  /** Why a square may not be on the card (null: it may) — THE POOL's order. */
  function reason(item, s) {
    if (!isMap(item) || !validId(item.id) || !has(MARKS, item.type) || item.type === "free") return "bad";
    if (!textIn(item, s.lang)) return "lang";
    var from = str(item.from), until = str(item.until);
    if (from || until) {
      if (!s.date || (from && s.date < from) || (until && s.date > until)) return "date";
    }
    if (s.pick[item.id] === 0) return "off";
    if (s.pick[item.id] === 1 || s.pin[item.id] === 1) return null;
    return soft(item, s);
  }
  // the filters a GVR can overrule by hand: the magazine, the occasion, the category
  function soft(item, s) {
    var pub = PUBS.indexOf(item.pub) >= 0 ? item.pub : "both";
    if (s.pub !== "both" && pub !== "both" && pub !== s.pub) return "pub";
    var w = wheresOf(item);
    if (s.where !== "any" && w.length && w.indexOf(s.where) < 0) return "where";
    if (s.cats[str(item.cat)] === false) return "cat";
    return null;
  }
  function why(item, s) { return reason(item, normalize(s)); }
  /** Offered at all in the card's language on the event's day (the builder lists only these). */
  function offered(item, s) {
    var r = reason(item, normalize(s));
    return r !== "bad" && r !== "lang" && r !== "date";
  }
  function pinnedIn(item, s) { return s.pin[item.id] === 1 || (item.pin === true && s.pin[item.id] !== 0); }
  function isPinned(item, s) { return isMap(item) && pinnedIn(item, normalize(s)); }
  function poolOf(items, s) {
    var seen = {}, all = [], pinned = [], info = [], rest = [];
    list(items).forEach(function (it) {
      if (reason(it, s) !== null || has(seen, it.id)) return;
      seen[it.id] = true;
      all.push(it);
      if (pinnedIn(it, s)) pinned.push(it);
      if (isInfo(it)) info.push(it);
      else if (!pinnedIn(it, s)) rest.push(it);
    });
    var cells = s.rows * s.cols, need = needOf(s);
    var infoTake = Math.min(info.length, s.infoMax);
    var have = pinned.filter(notInfo).length + infoTake + rest.length;
    return { pool: all, pinned: pinned, info: info, rest: rest, cells: cells, need: need, have: have, infoTake: infoTake,
             free: freeOn(s), ok: have >= need };
  }
  function pool(items, s) { return poolOf(items, normalize(s)); }
  /** { <cat>: n } — the squares of each category the card could have with that category on (the chips' counts). */
  function catCounts(items, s) {
    var n = normalize(s), out = {}, seen = {};
    CATS.forEach(function (c) { out[c] = 0; });
    list(items).forEach(function (it) {
      var r = reason(it, n);
      if (r === "cat") r = null;
      if (r !== null || has(seen, it.id)) return;
      seen[it.id] = true;
      var c = str(it.cat);
      out[c] = has(out, c) ? out[c] + 1 : 1;
    });
    return out;
  }
  /** New settings with that square taken in (on) or left out by hand. The map keeps only what the filters would not
   *  do by themselves; taking a square out also takes off an "always" set by hand (a row the CSV pins stays pinned
   *  but is out: pick 0 wins, and pickRows shows its "always" off). */
  function setPick(s, item, on) {
    var n = normalize(s);
    if (!isMap(item) || !validId(item.id)) return n;
    var id = item.id;
    delete n.pick[id];
    if (!on && n.pin[id] === 1) delete n.pin[id];
    var r = reason(item, n);
    if (on && (r === "pub" || r === "where" || r === "cat")) n.pick[id] = 1;
    if (!on && r === null) n.pick[id] = 0;
    return n;
  }
  /** New settings with that square pinned ("always on every card") or not. Pinning a square left out takes it in;
   *  unpinning one keeps it in when it was. */
  function setPin(s, item, on) {
    var n = normalize(s);
    if (!isMap(item) || !validId(item.id)) return n;
    var id = item.id, before = reason(item, n);
    delete n.pin[id];
    if (!!on !== (item.pin === true)) n.pin[id] = on ? 1 : 0;
    if (on && n.pick[id] === 0) delete n.pick[id];
    var r = reason(item, n), softly = r === "pub" || r === "where" || r === "cat";
    if (softly && (on || before === null)) n.pick[id] = 1;
    // a "taken in" the pin now does by itself goes
    if (n.pick[id] === 1) {
      delete n.pick[id];
      if (reason(item, n) !== null) n.pick[id] = 1;
    }
    return n;
  }
  /** The rows of the builder's "Choose squares yourself" (THE POOL): [{ item, on, pin }] for the squares offered. */
  function pickRows(items, s) {
    var n = normalize(s), out = [];
    list(items).forEach(function (it) {
      var r = reason(it, n);
      if (r === "bad" || r === "lang" || r === "date") return;
      out.push({ item: it, on: r === null, pin: r === null && pinnedIn(it, n) });
    });
    return out;
  }

  /* ------------------------------------------------------------------ the card */
  /** The card words with every field there: words (the page's) on top of WORDS[lang]. */
  function wordsFor(lang, words) {
    var base = WORDS[lang === "es" ? "es" : "en"], w = isMap(words) ? words : {};
    var lab = isMap(w.label) ? w.label : {};
    var out = { title: str(w.title) || base.title, free: str(w.free) || base.free, thisEvent: str(w.thisEvent) || base.thisEvent, label: {} };
    LABELLED.forEach(function (t) { out.label[t] = str(lab[t]) || base.label[t]; });
    return out;
  }
  /** {event} → the event's name, or "this event" / "este evento" when it has none. */
  function fillEvent(text, event, words) {
    var e = str(event).replace(/\s+/g, " ").trim();
    var w = isMap(words) ? str(words.thisEvent) : "";
    // (a function: a "$&" typed in the event's name stays as typed)
    return str(text).replace(/\{event\}/g, function () { return e || w || WORDS.en.thisEvent; });
  }
  // the squares of a list in the order of their keys (Efraimidis–Spirakis: u^(1/w), highest first — the same order
  // as ln(u) / w), ties by id
  function ranked(arr, seed) {
    return arr.map(function (it) {
      var u = 1 - rng(seed + ":" + it.id)();            // (0, 1]
      return { it: it, k: Math.log(u) / weightOf(it) };
    }).sort(function (a, b) { return b.k - a.k || (a.it.id < b.it.id ? -1 : a.it.id > b.it.id ? 1 : 0); })
      .map(function (x) { return x.it; });
  }
  function cellOf(it, s, w, dense) {
    var L = s.lang;
    var short = dense && isMap(it.short) ? str(it.short[L]).trim() : "";
    var lab = "";
    if (LABELLED.indexOf(it.type) >= 0) lab = (isMap(it.label) ? str(it.label[L]).trim() : "") || w.label[it.type] || "";
    return {
      id: it.id, free: false, type: it.type, cat: str(it.cat), pub: PUBS.indexOf(it.pub) >= 0 ? it.pub : "both",
      pin: pinnedIn(it, s), mark: MARKS[it.type], text: fillEvent(short || textIn(it, L), s.event, w), label: lab,
    };
  }
  function freeCell(s, w) {
    var t = str(s.freeText).replace(/\s+/g, " ").trim();
    return { id: "free", free: true, type: "free", cat: "", pub: "both", pin: false, mark: "free", text: t || w.free, label: "" };
  }
  function build(p, s, index, words, opts) {
    var w = wordsFor(s.lang, words);
    var seed = s.code + ":" + (s.same ? 0 : index);
    var need = p.need;
    // 1. the pinned squares but the info ones; 2. the info squares, the pinned ones first, up to infoTake; 3. the rest
    var picks = ranked(p.pinned.filter(notInfo), seed).slice(0, need);
    var infoN = Math.min(p.infoTake, need - picks.length);
    var pinnedInfo = ranked(p.info.filter(function (it) { return pinnedIn(it, s); }), seed);
    var otherInfo = ranked(p.info.filter(function (it) { return !pinnedIn(it, s); }), seed);
    picks = picks.concat(pinnedInfo.concat(otherInfo).slice(0, infoN));
    picks = picks.concat(ranked(p.rest, seed).slice(0, need - picks.length));
    // the places: Fisher–Yates
    var rand = rng(seed);
    for (var i = picks.length - 1; i > 0; i--) {
      var j = Math.floor(rand() * (i + 1));
      var t = picks[i]; picks[i] = picks[j]; picks[j] = t;
    }
    // (the page's measured answer when it gives one, else the estimate)
    var dense = isMap(opts) && typeof opts.dense === "boolean" ? opts.dense : denseOf(s);
    var centre = p.free ? Math.floor(s.rows / 2) * s.cols + Math.floor(s.cols / 2) : -1;
    var cells = [], k = 0;
    for (var c = 0; c < s.rows * s.cols; c++) cells.push(c === centre ? freeCell(s, w) : cellOf(picks[k++], s, w, dense));
    return { index: index, code: s.code, lang: s.lang, rows: s.rows, cols: s.cols, dense: dense, free: p.free, cells: cells };
  }
  /** The card takes the squares' short words: a big grid (rows or cols ≥ DENSE), or squares smaller than SMALL_CELL
   *  inches on its printed sheet, as cardPlan estimates them (the page passes what it measured instead: opts.dense). */
  function denseOf(s) {
    var n = normalize(s);
    return n.rows >= DENSE || n.cols >= DENSE || cardPlan(n).cell < SMALL_CELL;
  }
  function shortOf(p) { return { error: "short", have: p.have, need: p.need }; }
  /** One card (index from 0), or { error: "short", have, need }. opts: { dense } (THE CARD). */
  function card(items, s, index, words, opts) {
    var n = normalize(s), p = poolOf(items, n);
    if (!p.ok) return shortOf(p);
    var i = Math.max(0, Math.floor(num(index)) || 0);
    return build(p, n, i, words, opts);
  }
  /** s.count cards, or { error: "short", have, need }. opts: as card()'s. */
  function cards(items, s, words, opts) {
    var n = normalize(s), p = poolOf(items, n);
    if (!p.ok) return shortOf(p);
    var out = [], first = null;
    for (var i = 0; i < n.count; i++) {
      if (n.same && first) {
        var c = copy(first);
        c.index = i;
        out.push(c);
      } else {
        first = build(p, n, i, words, opts);
        out.push(first);
      }
    }
    return out;
  }
  /** Every square the pool may put on a card, as card() draws it, once each (THE CARD), or [] (too few squares). */
  function poolCells(items, s, words, opts) {
    var n = normalize(s), p = poolOf(items, n);
    if (!p.ok) return [];
    var w = wordsFor(n.lang, words);
    var dense = isMap(opts) && typeof opts.dense === "boolean" ? opts.dense : denseOf(n);
    // (build's steps: the pinned squares but the info ones, all of them may win a place; then infoN info squares —
    // the pinned ones only when they are that many —; then the rest, when places are left)
    var pinned = p.pinned.filter(notInfo), room = p.need - Math.min(pinned.length, p.need);
    var infoN = Math.min(p.infoTake, room);
    var pinnedInfo = p.info.filter(function (it) { return pinnedIn(it, n); });
    var may = {};
    pinned.concat(infoN === 0 ? [] : pinnedInfo.length >= infoN ? pinnedInfo : p.info, room > infoN ? p.rest : [])
      .forEach(function (it) { may[it.id] = true; });
    return p.pool.filter(function (it) { return may[it.id] === true; }).map(function (it) { return cellOf(it, n, w, dense); });
  }

  /* ------------------------------------------------------------------ the link */
  // the address's keys: [settings key, kind]
  var HASH = {
    grid: ["grid", "grid"], free: ["free", "bool"], freetext: ["freeText", "text"], cards: ["count", "int"],
    same: ["same", "bool"], code: ["code", "code"], per: ["perSheet", "per"], paper: ["paper", "enum"],
    orient: ["orient", "enum"], bw: ["color", "notbool"], lang: ["lang", "enum"], mag: ["pub", "enum"],
    where: ["where", "enum"], off: ["cats", "cats"], info: ["infoMax", "int"], "in": ["pick", "ids1"],
    out: ["pick", "ids0"], pin: ["pin", "ids1"], unpin: ["pin", "ids0"], names: ["showName", "bool"],
    howto: ["showRules", "bool"], rules: ["rules", "text"], strip: ["showInfo", "bool"], title: ["title", "text"],
    event: ["event", "text"], date: ["date", "date"],
  };
  var HASH_ORDER = ["grid", "code", "cards", "same", "lang", "mag", "where", "title", "event", "date", "free", "freetext",
    "off", "info", "in", "out", "pin", "unpin", "per", "paper", "orient", "bw", "names", "howto", "rules", "strip"];
  function idList(map, flag) { return Object.keys(map).filter(function (id) { return map[id] === flag; }).sort().join("."); }
  /** The settings as the address's #hash: the grid, the code and the card's language always (the language: a link
   *  made on /es/ opened on the English page — whose own default is English — still makes Spanish cards), the rest
   *  only where it is not the default. */
  function encode(s) {
    var n = normalize(s), parts = [];
    function put(k, v) { parts.push(k + "=" + encodeURIComponent(v)); }
    function b(v) { return v ? "1" : "0"; }
    HASH_ORDER.forEach(function (k) {
      var key = HASH[k][0], kind = HASH[k][1], v;
      if (k === "lang") { put(k, n.lang); return; }
      switch (kind) {
        case "grid": put(k, n.rows + "x" + n.cols); return;
        case "code": if (n.code) put(k, n.code); return;
        case "cats": v = Object.keys(n.cats).sort().join("."); if (v) put(k, v); return;
        case "ids1": v = idList(n[key], 1); if (v) put(k, v); return;
        case "ids0": v = idList(n[key], 0); if (v) put(k, v); return;
        case "notbool": if (n[key] !== DEF[key]) put(k, b(!n[key])); return;
        case "bool": if (n[key] !== DEF[key]) put(k, b(n[key])); return;
        default: if (n[key] !== DEF[key]) put(k, String(n[key]));
      }
    });
    return "#" + parts.join("&");
  }
  function idsIn(v) {
    var out = [];
    v.split(".").forEach(function (id) { if (validId(id) && out.length < PICK_MAX) out.push(id); });
    return out;
  }
  // one key of the address into the part `out` (strict: a bad value is skipped)
  function take(out, k, v) {
    if (!has(HASH, k)) return;
    var key = HASH[k][0], kind = HASH[k][1], m, n;
    switch (kind) {
      case "grid":
        m = /^(\d{1,2})x(\d{1,2})$/.exec(v);
        if (m && +m[1] >= LIMITS.rows[0] && +m[1] <= LIMITS.rows[1] && +m[2] >= LIMITS.cols[0] && +m[2] <= LIMITS.cols[1]) {
          out.rows = +m[1];
          out.cols = +m[2];
        }
        return;
      case "bool": if (v === "1" || v === "0") out[key] = v === "1"; return;
      case "notbool": if (v === "1" || v === "0") out[key] = v === "0"; return;
      case "int":
        if (!/^\d{1,2}$/.test(v)) return;
        n = +v;
        if (n >= LIMITS[key][0] && n <= LIMITS[key][1]) out[key] = n;
        return;
      case "per": if (/^[124]$/.test(v)) out[key] = +v; return;
      case "enum": if (ENUMS[key].indexOf(v) >= 0) out[key] = v; return;
      case "code": if (cleanCode(v) && cleanCode(v) === v.toUpperCase()) out[key] = cleanCode(v); return;
      case "date": if (day(v) === v) out[key] = v; return;
      case "text":
        if (v.length <= TEXT_MAX[key] && !/[\u0000-\u0009\u000b-\u001f\u007f]/.test(v) && (key === "rules" || v.indexOf("\n") < 0)) out[key] = v;
        return;
      case "cats":
        var cats = {};
        v.split(".").forEach(function (c) { if (CAT_ID.test(c)) cats[c] = false; });
        if (Object.keys(cats).length) out.cats = cats;
        return;
      case "ids1": case "ids0":
        var ids = idsIn(v);
        if (!ids.length) return;
        if (!isMap(out[key])) out[key] = {};
        ids.forEach(function (id) { out[key][id] = kind === "ids1" ? 1 : 0; });
        return;
    }
  }
  /** The settings the address's #hash holds (a part: only what it names, each value strictly; never throws). */
  function decode(hash) {
    var out = {};
    try {
      var h = str(hash);
      if (h.charAt(0) === "#") h = h.slice(1);
      if (!h || h.length > HASH_MAX) return out;
      h.split("&").forEach(function (part) {
        var eq = part.indexOf("=");
        if (eq < 1) return;
        var v;
        try { v = decodeURIComponent(part.slice(eq + 1).replace(/\+/g, " ")); } catch (e) { return; }
        take(out, part.slice(0, eq), v);
      });
    } catch (e) {
      return {};
    }
    return out;
  }
  /** A link's whole settings (on the defaults and base, never on a device's own), or null: no bingo setting in it. */
  function fromHash(hash, base) {
    var part = decode(hash);
    return Object.keys(part).length ? normalize(part, base) : null;
  }

  /* ------------------------------------------------------------------ the sheet */
  /** The printed page and each card's place on it, in inches (THE SHEET). */
  function sheetPlan(s) {
    var n = normalize(s);
    var p = PAPERS[n.paper], land = n.orient === "landscape";
    var page = { w: land ? p.h : p.w, h: land ? p.w : p.h };
    var area = { w: r3(page.w - 2 * MARGIN), h: r3(page.h - 2 * MARGIN) };
    var per = perSheetOf(n), across = 1, down = 1;
    if (per === 2) { if (area.h >= area.w) down = 2; else across = 2; }
    if (per === 4) { across = 2; down = 2; }
    var sw = r3((area.w - GAP * (across - 1)) / across), sh = r3((area.h - GAP * (down - 1)) / down);
    var slots = [];
    for (var r = 0; r < down; r++) {
      for (var c = 0; c < across; c++) slots.push({ x: r3(c * (sw + GAP)), y: r3(r * (sh + GAP)), w: sw, h: sh });
    }
    return {
      paper: n.paper, orient: n.orient, size: (n.paper === "a4" ? "A4" : "letter") + " " + n.orient, page: page,
      margin: MARGIN, area: area, gap: GAP, perSheet: per, across: across, down: down, slots: slots,
      count: n.count, sheets: Math.ceil(n.count / per),
    };
  }
  // one card's parts at full size (a card the size of a Letter page's area, 7.7 × 10.2 in), in inches, as bingo.css
  // draws them (measured in Chrome): the head, the name lines, how to play and the meetings strip (side by side under
  // the grid — the strip, with its QR code, the taller), the small print, the gap between parts, the card's padding
  // (pad, its 1pt border on top: BORDER) and the narrowest column beside the grid on a wide card (side). LINES: the
  // grid's lines and the room around them (bingo.css .bgo-grid --c). SIDE_TALL: how much taller each part is in
  // that column than across the card (narrower: more lines; the two name lines one above the other).
  var PART = { header: 0.66, names: 0.24, rules: 0.6, info: 1.28, qr: 0.82, foot: 0.2, gap: 0.1, pad: 0.2, side: 2.2 };
  var SIDE_TALL = { header: 1.65, names: 2.15, rules: 1.8, info: 1.95 };
  var BORDER = 1 / 72, LINES = 3.75 / 72;
  var FULL = { w: 7.7, h: 10.2 };
  function floorCell(v) { return Math.floor(Math.max(0.2, v) * 100) / 100; }
  /** An estimate of one card in its slot (THE SHEET), in inches: "stack" or, when its squares come out 5 % bigger
   *  so and the column fits, "side" (the header says which is which). */
  function cardPlan(s, slot) {
    var n = normalize(s);
    var sl = isMap(slot) && isNum(slot.w) && isNum(slot.h) && slot.w > 0 && slot.h > 0 ? slot : sheetPlan(n).slots[0];
    var k = clamp(Math.sqrt((sl.w * sl.h) / (FULL.w * FULL.h)), 0.6, 1);
    var parts = { header: PART.header * k, names: n.showName ? PART.names * k : 0, rules: n.showRules ? PART.rules * k : 0,
                  info: n.showInfo ? PART.info * k : 0, foot: PART.foot * k };
    var gap = PART.gap * k, edge = 2 * (PART.pad * k + BORDER);
    var w = sl.w - edge, h = sl.h - edge;
    // stack: head, [names], the body (the grid, then how to play beside the strip), the small print — a gap between
    // each two of them, and one in the body
    var under = Math.max(parts.rules, parts.info);
    var used = parts.header + (parts.names ? parts.names + gap : 0) + (under ? under + gap : 0) + parts.foot + 2 * gap;
    var stack = floorCell(Math.min((w - LINES) / n.cols, (h - used - LINES) / n.rows));
    var cell = stack, side = { w: 0, h: 0 };
    // side: the grid the whole height but the small print's; the column gets what the grid cannot use (the
    // squares as tall as the height lets them be), at least side × the scale — and, when its parts are taller than
    // the grid at that width, wider in steps (its words then take fewer lines), at most 55 % of the card: as
    // bingo.js chooseLayout does it, measuring
    var colGap = gap * 1.6, gridH = h - parts.foot - gap, tall = (gridH - LINES) / n.rows, least = PART.side * k;
    for (var sw = clamp(w - colGap - LINES - n.cols * tall, least, w * 0.55); sw <= w * 0.55 + 1e-9; sw += Math.max(0.09, w * 0.05)) {
      var f = least / sw;
      var sh = parts.header * SIDE_TALL.header * f + gap + parts.names * SIDE_TALL.names + gap +
               (parts.rules * SIDE_TALL.rules + parts.info * SIDE_TALL.info) * f + (parts.rules && parts.info ? 0.8 * gap : 0);
      if (sh > gridH) continue;
      var beside = floorCell(Math.min((w - sw - colGap - LINES) / n.cols, tall));
      if (beside > stack * 1.05) {
        cell = beside;
        side = { w: r3(sw), h: r3(sh) };
      }
      break;
    }
    return {
      layout: side.w ? "side" : "stack", w: r3(sl.w), h: r3(sl.h), scale: r3(k), header: r3(parts.header),
      names: r3(parts.names), rules: r3(parts.rules), info: r3(parts.info), qr: n.showInfo ? r3(PART.qr * k) : 0,
      foot: r3(parts.foot), gap: r3(gap), side: side, grid: { w: r3(cell * n.cols), h: r3(cell * n.rows) }, cell: cell,
    };
  }
  /** { sheet: sheetPlan(s), card: cardPlan(s, its first slot) }. */
  function layout(s) {
    var sheet = sheetPlan(s);
    return { sheet: sheet, card: cardPlan(s, sheet.slots[0]) };
  }

  /* ------------------------------------------------------------------ text size */
  // the letters' widths in hundredths of an em: Inter (the site's font) at weight 600 — the widest the cards use —,
  // measured in Chrome; the space at weight 400 (its widest); an accented letter as its letter; anything else 62
  var EM_LOWER = [57, 62, 58, 62, 59, 35, 63, 61, 26, 26, 57, 26, 90, 61, 61, 62, 62, 41, 55, 35, 61, 59, 84, 57, 59, 57];
  var EM_UPPER = [74, 66, 74, 72, 61, 59, 75, 75, 28, 58, 70, 57, 92, 76, 77, 65, 77, 65, 65, 66, 74, 74, 104, 72, 71, 65];
  var EM_DIGIT = [66, 42, 62, 64, 67, 61, 64, 59, 64, 64];
  var EM_OTHER = { " ": 28, ".": 32, ",": 32, ";": 33, ":": 32, "'": 33, "!": 32, "?": 54, "¿": 54, "¡": 32, "(": 37,
                   ")": 37, "&": 66, "@": 100, "%": 100, "-": 47, "–": 50, "—": 100, "·": 32, "/": 38, "#": 64,
                   "’": 29, "\"": 52, "“": 45, "”": 45 };
  var EM_SAFE = 1.03;
  function charEm(ch) {
    var c = ch.charCodeAt(0);
    if (c >= 97 && c <= 122) return EM_LOWER[c - 97] / 100;
    if (c >= 65 && c <= 90) return EM_UPPER[c - 65] / 100;
    if (c >= 48 && c <= 57) return EM_DIGIT[c - 48] / 100;
    if (has(EM_OTHER, ch)) return EM_OTHER[ch] / 100;
    var base = ch;
    try { base = ch.normalize("NFD").charAt(0); } catch (e) { /* an old browser: the default width */ }
    return base !== ch ? charEm(base) : 0.62;
  }
  function wordEm(w) {
    var e = 0;
    for (var i = 0; i < w.length; i++) e += charEm(w.charAt(i));
    return e * EM_SAFE;
  }
  // the lines the words take at f pt in a box w inches wide (Infinity: a word does not fit and may not be broken)
  function linesAt(words, f, w, hyphens) {
    var em = f / 72, space = (EM_OTHER[" "] / 100) * em, lines = 1, x = 0;
    for (var i = 0; i < words.length; i++) {
      var ww = wordEm(words[i]) * em;
      if (ww > w) {
        if (!hyphens) return Infinity;
        if (x > 0) lines++;
        var pieces = Math.ceil(ww / (w * 0.92));
        lines += pieces - 1;
        x = ww - (pieces - 1) * w * 0.92;
        continue;
      }
      if (x === 0) x = ww;
      else if (x + space + ww <= w) x += space + ww;
      else { lines++; x = ww; }
    }
    return lines;
  }
  // the room a square's mark takes under its words: [share of the square, at least, at most] (inches)
  var RESERVE = { line: [0.3, 0.16, 0.5], box: [0.24, 0.14, 0.4], tick: [0.16, 0.1, 0.3], icon: [0.16, 0.1, 0.3], free: [0, 0, 0] };
  // an address and its places to break (bingo.js ADDRESS / breakable and the sample's bingoBreaks: the same — an
  // e-mail after its "@" only, the site's after "/" and before "."): here a space, so each piece is a word (a space's
  // width more than the page draws: the guess stays on the safe side)
  var ADDRESS = /\S*@\S+|\S+\.(?:org|com|net|io|edu|gov|us)(?:\/\S*)?/gi;
  function addressPieces(text) {
    return text.replace(ADDRESS, function (a) {
      return a.indexOf("@") >= 0 ? a.replace(/@(?=\S)/g, "@ ") : a.replace(/\/(?=\S)/g, "/ ").replace(/(\S)\.(?=\S)/g, "$1 .");
    });
  }
  /** A starting font size (pt) for a square's words: the biggest, in steps of 0.5, whose word wrap fits the square
   *  above its mark; MIN_PT at the least. */
  function fontGuess(text, cellInches, mark) {
    var c = isNum(cellInches) && cellInches > 0 ? cellInches : 1;
    var m = mark === true ? "line" : mark === false || !has(RESERVE, mark) ? "tick" : mark;
    var res = RESERVE[m];
    var pad = clamp(c * 0.06, 0.035, 0.1);
    var w = c - 2 * pad, h = c - 2 * pad - clamp(c * res[0], res[1], res[2]);
    var words = addressPieces(str(text)).replace(/\s+/g, " ").trim().split(" ").filter(Boolean);
    if (!words.length || h <= 0) return MIN_PT;
    var max = clamp(Math.floor(c * 72 * (m === "free" ? 0.3 : 0.17) * 2) / 2, 7, m === "free" ? 36 : MAX_PT);
    for (var f = max; f >= MIN_PT; f -= 0.5) {
      if (linesAt(words, f, w, f <= 8) * f * 1.18 / 72 <= h) return f;
    }
    return MIN_PT;
  }
  // a typed title or event in the card's head: a long piece of it (a pasted link, an e-mail, a hashtag — HEAD_PIECE
  // characters or more with no space) may go on two lines after a "/", ".", "@", "-" or "_" inside it (a run of them:
  // "https://" stays whole), and between a small letter and a capital ("#NETA65Grapevine" / "LaVina"). Shorter pieces
  // never break ("A.A." stays whole).
  var HEAD_PIECE = 12;
  var HEAD_CUT = /[\/.@_-]+(?=[^\s\/.@_-])|[a-z\u00df-\u00f6\u00f8-\u00ff](?=[A-Z\u00c0-\u00d6\u00d8-\u00de])/g;
  /** The words of a typed title or event in pieces, a line free to break between two (their join is the words). */
  function headPieces(text) {
    var s = str(text), out = [], at = 0, word = /\S+/g, w, m;
    while ((w = word.exec(s))) {
      if (w[0].length < HEAD_PIECE) continue;
      HEAD_CUT.lastIndex = 0;
      while ((m = HEAD_CUT.exec(w[0]))) {
        if (!m.index) continue;               // (never before the piece's first letter: "iPhone" stays whole)
        var cut = w.index + m.index + m[0].length;
        out.push(s.slice(at, cut));
        at = cut;
      }
    }
    out.push(s.slice(at));
    return out;
  }

  /* ------------------------------------------------------------------ the module */
  root.GVBingo = {
    VERSION: VERSION, LANGS: LANGS, PUBS: PUBS, WHERES: WHERES, CATS: CATS, MARKS: copy(MARKS), LABELLED: LABELLED,
    PAPERS: copy(PAPERS), ORIENTS: ORIENTS, PER_SHEET: PER_SHEET, LIMITS: copy(LIMITS), TEXT_MAX: copy(TEXT_MAX),
    DENSE: DENSE, SMALL_CELL: SMALL_CELL, ALPHABET: ALPHABET, MARGIN: MARGIN, GAP: GAP, SIDE: PART.side, MIN_PT: MIN_PT,
    MAX_PT: MAX_PT, WORDS: copy(WORDS), DEFAULTS: copy(DEF),
    // the settings
    normalize: normalize, cleanCode: cleanCode, newCode: newCode,
    // (each of these four normalizes what it is given first)
    freeOn: function (s) { return freeOn(normalize(s)); }, needOf: function (s) { return needOf(normalize(s)); },
    perSheetOf: function (s) { return perSheetOf(normalize(s)); },
    perSheetChoices: function (s) { return perSheetChoices(normalize(s)); },
    // chance
    rng: rng, seedOf: seedOf,
    // the pool
    why: why, offered: offered, isPinned: isPinned, pool: pool, catCounts: catCounts, setPick: setPick, setPin: setPin,
    pickRows: pickRows,
    // the card
    wordsFor: wordsFor, fillEvent: fillEvent, denseOf: denseOf, card: card, cards: cards, poolCells: poolCells,
    // the link
    encode: encode, decode: decode, fromHash: fromHash,
    // the sheet, text size, the head
    sheetPlan: sheetPlan, cardPlan: cardPlan, layout: layout, fontGuess: fontGuess, headPieces: headPieces,
  };
})(typeof window !== "undefined" ? window : globalThis);
