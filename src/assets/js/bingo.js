/* The Grapevine & La Viña Bingo builder on /gvr/bingo/ (src/pages/gvr-bingo.njk): the page's Alpine component,
   "bingoBuilder". The cards' logic — the settings, the pool, the seeded draw, the link, the sheet plan — is
   bingo-core.js (window.GVBingo, loaded just before this file; tests/test_r34_bingo.py); this file is the screen:
     · the settings form (six groups: your game, grid, where, squares — with "Choose squares yourself", one folded
       list a kind of squares, GVBingo.pickRows —, cards, on each card), every change normalized by
       GVBingo.normalize and drawn at once in the preview — the typed words (title, event, free square, How to play)
       a moment after the last key (TYPE_WAIT: a big card takes a slow phone a third of a second to draw);
     · the preview: the real card (the same DOM that prints), in inches and points, scaled to its column — beside
       the settings from 1024px, no taller than the column leaves it under the buttons, the print help and the sheet
       line (scale) —; "Card 3 of 10" with previous / next; "Actual size" when the card is drawn smaller than
       ZOOM_UNDER (a phone: the card at its paper size, scrolled sideways in its box);
     · the layout, measured (LAYOUT below): "stack", "side" or "top", the meetings strip's long, mid or short lines,
       the head's size and date, and the short words (dense) when the squares come out smaller than
       GVBingo.SMALL_CELL — whatever keeps every square at 6 pt;
     · the text fitting: every square's words are MEASURED and shrunk until they fit their box (no overflow, no
       clipping: any grid 3×3–10×10, rectangular too, both languages, Letter and A4, 1, 2 or 4 on a sheet) — see
       fitCards;
     · printing: "Print or save as PDF" (and the browser's own Print, on beforeprint) fills #bgo-print with the
       sheets, fits them, puts the paper's size in an @page rule of its own (a <style> added while printing — the
       stylesheets have no unnamed @page; its margin is 0 and each sheet carries the margin as its own padding, so
       the print window has no room for its "Headers and footers") and html[data-print="bingo"] (bingo.css: only
       the cards go on paper); afterprint takes it all away again. The button waits for the fonts and makes the
       sheets a few cards at a time (the page answers meanwhile; "Getting 60 cards ready… 20 of 60"); the browser's
       own Print cannot wait, so it makes them all at once;
     · the link: "Copy a link to these settings" puts the settings in the address's #hash (GVBingo.encode) and copies
       it; a page opened with one makes the very same cards (GVBingo.fromHash, on the defaults); while the address
       holds a link it follows every change (history.replaceState);
     · memory: the last settings are kept in this browser (localStorage "gv-bingo:v1": { v, page, s }) — a first
       visit's game code at once, and what was printed or linked as it was —; everything works without it (a
       private window, storage blocked). A remembered date in the past becomes today; the card language comes back
       only on the page language it was chosen on (the other page's default is its own). Squares and categories the
       page does not have (a link or a memory from before a CSV row was removed) are dropped (onlyKnown).
     · "Start over" asks first, in the page (unless nothing differs from a fresh start but the code), then forgets
       it all: the starting settings, a new code, today's date.
   window.GVBingoBuilder = true says this file ran: the page's notice outside the component shows when it did not.
   The squares (#bingo-data: bingo.items, filled and checked at build by eleventy/filters/bingo.js), the facts the
   cards print (bingo.info), the card words of BOTH languages (src/_i18n/bingo.json bingo.card.*) and the builder's
   own (bingo.ui.*, the page's language) come from the page; the icons from <template id="bgo-icons"> (copied); the
   QR codes are SVG symbols the build drew (#bgo-qr-en / #bgo-qr-es). Never innerHTML: every word the CSV or the
   visitor wrote goes in with textContent / x-text.

   FITTING — a square: .bgo-cell (a flex column: its words' box .bgo-txt, then its mark .bgo-mk) and the words
   themselves, .bgo-w, a block inside the box. A size fits when the words are no taller than their box (1px to
   spare: paper and screen round differently), and — above HY_AT pt — no word is wider than the box (no hyphens
   there; at HY_AT and below the words may break, with the card's lang's hyphens). Squares with the same words, mark
   and label are the same in every card of a run (one size of square for all), so each is measured once: a batched
   binary search over 0.5 pt steps from MIN_FIT to the square's top size (about a fifth of the square's height,
   MAX_PT at most; FREE up to 36), every probe written for all of them first and read for all of them after (one
   layout per step, ~6 steps). Then, card by card, no square's words more than HARMONY × the card's middle size
   (a short square next to long ones would shout), and a last check that shrinks anything that still sticks out.

   LAYOUT — the preview card decides for the whole run (every card of it the same size, the same parts): placeCard
   tries the strip's lines — "long" ("1st Wednesday of the month, 7 – 8 PM Central, Google Meet"), "mid" ("1st Wed ·
   7 PM · Google Meet"), "short" ("1st Wed · 7 PM"): bingo.info gvMeeting / gvMeetingMid / gvMeetingShort, the same
   for the committee meeting — and the head's steps (HEAD_STEPS: a typed title or event gets a short date, then
   smaller words, then the event without its date); for each it lays the card out (chooseLayout: "stack", "side" or
   "top", at the narrowest side column that fits — a wider one, or another layout, only to keep more of the head's
   words whole, when its squares are no more than WHOLE_COST smaller and no more of them miss the floor) and measures
   the squares, and the short words when they come out smaller than GVBingo.SMALL_CELL inches (the core's card(…,
   { dense })). THE FLOOR decides: every square the run may draw (GVBingo.poolCells, each once, in a hidden grid of the
   same squares: floorMisses) still prints at MIN_PT or more, with nothing sticking out — or, when some square cannot
   at all (a CSV row too long for squares this small), no more of them than with the shortest lines and the smallest
   head at the narrowest layout. Head step by head step from the head as it is, the lines that say where we meet
   ("long", then "mid"; "long" only while its squares are no more than LONG_COST smaller than with "mid": the two
   differ only by the time zone) — and the "short" lines only when neither keeps the floor at any step. So the
   meeting place prints wherever it fits, the head is made smaller only when even the "mid" lines need it, and a
   long typed title or event never pushes the squares' words under 6 pt while a smaller head can keep them there
   (the builder says so under the Event box: headCut) — a pasted link breaks after its "/" and "." instead
   (GVBingo.headPieces, headIn), a word with no place to break breaks anywhere. A small card (2 or 4 on a sheet:
   under COMPACT_IN) prints the short "How to play" when the typed one is longer than RULES_COMPACT_MAX (the builder
   says so under its box). The floor's counts are kept for the run (M.keep: the pager and a redraw measure nothing
   again) until the settings or the fonts change, and what it measured of each square for as long as the fonts, the
   card's language and the page's look stay the same (M.floor: a change of the title or the event measures again
   only the squares it changed, and only where what was measured before does not tell already). */
(function () {
  "use strict";

  window.GVBingoBuilder = true;
  // the core's numbers (bingo-core.js, loaded just before this file); the ones after || only matter when it did not
  // load — and then the builder says it could not start
  var CORE = window.GVBingo || {};
  var KEY = "gv-bingo:v1";
  var SVG_NS = "http://www.w3.org/2000/svg";
  var PX_IN = 96;
  var SAFE_H = 0.04;      // inches off the printed area's height: a rounding never pushes a sheet onto a blank page
  var MIN_PT = CORE.MIN_PT || 6;   // pt: whole words at this size or more are taken over bigger words cut in two
  var MIN_FIT = 5;        // pt: the last resort, for words too long for their square even at MIN_PT with hyphens
                          //  (placeCard keeps every square at MIN_PT or more whenever a layout can: only a CSV row
                          //  too long for squares this small whatever the layout gets here)
  var HY_AT = 8;          // pt: at this size and below, words may break (hyphens)
  var COMPACT_IN = 5.2;   // a card narrower or shorter than this (2 or 4 on a sheet): the short "How to play"
  var RULES_COMPACT_MAX = 140;   // characters of a typed "How to play" a small card still prints (the default
                                 //  short ones are about 125)
  var HARMONY = 1.35;
  var SIDE_IN = CORE.SIDE || 2.2;   // the side column of a wide card at its narrowest (× the card's scale)
  var SMALL_CELL = CORE.SMALL_CELL || 1.2, DENSE = CORE.DENSE || 7;
  // the head, step by step, while the squares would print under MIN_PT even with the "mid" meeting lines (placeCard):
  // [the date ("long": "Wednesday, November 18, 2026"; "short": "Nov 18, 2026"; "none": the event's name alone), the
  // title's and the event's size against the stylesheet's]. A typed title or event takes them all; a small card's own
  // head only the short date; any other head stays as it is
  var HEAD_STEPS = [["long", 1], ["short", 1], ["short", 0.85], ["short", 0.7], ["none", 0.7]];
  // the "long" meeting lines' cost, at most: their squares no more than this much smaller than with the "mid" ones
  // (both say where we meet; "long" adds the time zone — not worth a third of the squares' size on a small card)
  var LONG_COST = 0.08;
  // a side column made wider to keep the head's words whole (chooseLayout): its squares no more than this much smaller
  // than at the narrowest width — and never with more squares under the floor there (placeCard)
  var WHOLE_COST = 0.1;
  var FLOOR_FIRST = 24;   // squares the floor measures first, the likeliest to miss (floorMisses)
  var FLOOR_KEEP = 4000;  // squares the floor's store keeps at most (M.floor: more, and it starts again)
  var SMALL_WRITE = 1.15; // squares smaller than this (inches) leave little room to write: the builder says so
  var CHUNK = 4;          // cards made at a time for "Print or save as PDF" (a frame for the page between)
  // the settings typed letter by letter: the preview is drawn TYPE_WAIT ms after the last key (none of them changes
  // the pool: only the card's words)
  var TYPED = { title: 1, event: 1, freeText: 1, rules: 1 }, TYPE_WAIT = 220;
  var ZOOM_UNDER = 0.8;   // the preview drawn smaller than this: "Actual size" is offered
  var K_LEAST = 0.3;      // the stuck preview column's card never smaller than this (a shorter window: the column scrolls)

  /* ---------------- small helpers ---------------- */
  function fmt(tpl, vars) {
    return String(tpl == null ? "" : tpl).replace(/\{(\w+)\}/g, function (m, k) { return vars && vars[k] != null ? String(vars[k]) : m; });
  }
  function clamp(n, lo, hi) { return n < lo ? lo : n > hi ? hi : n; }
  function r3(n) { return Math.round(n * 1000) / 1000; }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  function lsGet(k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { window.localStorage.setItem(k, v); return true; } catch (e) { return false; } }
  var YMD = /^\d{4}-\d{2}-\d{2}$/;
  /** Today in the site's time zone (Central): GVTime (central-time.js, every page), else Intl, else the device. */
  function todayCentral() {
    var tz = (window.SITE && window.SITE.tz) || "America/Chicago";
    try {
      if (window.GVTime && typeof window.GVTime.ymdOf === "function") {
        var y = window.GVTime.ymdOf(Date.now(), tz);
        if (YMD.test(y)) return y;
      }
    } catch (e) { /* the next way */ }
    try {
      var s = new Intl.DateTimeFormat("en-CA", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
      if (YMD.test(s)) return s;
    } catch (e) { /* the device's day */ }
    // (the device's own day, never UTC's: an evening in Texas is not tomorrow)
    var d = new Date();
    return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2);
  }
  // (a date's year never alone on a line under the title: a no-break space before it)
  function yearKept(s) { return s.replace(/ (\d{4})$/, "\u00a0$1"); }
  /** "Tuesday, November 17, 2026" / "Martes, 17 de noviembre de 2026" — the build's fmtDate(…, "long"). */
  function longDate(ymd, lang) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(ymd || "");
    if (!m) return "";
    try {
      var s = new Intl.DateTimeFormat(lang === "es" ? "es-US" : "en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric", timeZone: "UTC" })
        .format(new Date(Date.UTC(+m[1], +m[2] - 1, +m[3], 12)));
      return yearKept(lang === "es" ? s.charAt(0).toUpperCase() + s.slice(1) : s);
    } catch (e) { return ymd; }
  }
  /** "Nov 18, 2026" / "18 nov 2026" — a small card's date when its head needs the room (HEAD_STEPS). */
  function shortDate(ymd, lang) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(ymd || "");
    if (!m) return "";
    try {
      return yearKept(new Intl.DateTimeFormat(lang === "es" ? "es-US" : "en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" })
        .format(new Date(Date.UTC(+m[1], +m[2] - 1, +m[3], 12))));
    } catch (e) { return ymd; }
  }
  /** Words to search in: lower case, without accents. */
  function fold(v) {
    var s = String(v == null ? "" : v).toLowerCase();
    try { s = s.normalize("NFD").replace(/[\u0300-\u036f]/g, ""); } catch (e) { /* an old browser: as it is */ }
    return s;
  }
  /** An attribute set only when it changes (setting the same value again would still make the browser work out
   *  the element's styles anew: placeCard sets them again and again). */
  function setAttr(e, name, value) { if (e.getAttribute(name) !== value) e.setAttribute(name, value); }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = String(text);
    return e;
  }
  /** One of the page's icons (<template id="bgo-icons">), copied — or null. */
  function icon(name) {
    var t = document.getElementById("bgo-icons");
    var src = t && t.content ? t.content.querySelector('[data-i="' + name + '"] svg') : null;
    return src ? src.cloneNode(true) : null;
  }

  /* ---------------- the card's DOM (the same markup as the page's no-JS sample: gvr-bingo.njk sampleCard) ---------------- */
  /** The words the core's card() takes (GVBingo.wordsFor's shape) from the page's card words of one language. */
  function coreWords(cw) {
    cw = cw || {};
    return { title: cw.title, free: cw.free, thisEvent: cw.this_event,
             label: { name: cw.label_name, phone: cw.label_phone, write: cw.label_write, sign: cw.label_sign } };
  }
  /** A square's words with a place to break in an address (a zero-width space): an e-mail after its "@" only
   *  ("grapevine@" / "neta65.org" — "grapevine@neta65" / ".org" would read as a whole, wrong address), the site's
   *  after a "/" and before a "." — so it can go on two lines whole, never cut in a word. bingo-core.js addressPieces
   *  and the no-JS sample's filter bingoBreaks (eleventy/filters/bingo-sample.js) break the same way. */
  var ADDRESS = /\S*@\S+|\S+\.(?:org|com|net|io|edu|gov|us)(?:\/\S*)?/gi;
  function breakable(text) {
    return String(text).replace(ADDRESS, function (a) {
      return a.indexOf("@") >= 0 ? a.replace(/@(?=\S)/g, "@\u200b") : a.replace(/\/(?=\S)/g, "/\u200b").replace(/(\S)\.(?=\S)/g, "$1\u200b.");
    });
  }
  /** Words into an element as text, each time range ("7 – 8 PM", "7–8 p. m.") in a span kept on one line (bingo.css
   *  .bgo-nb: "7 –" / "8 PM" is no time) — the same text, so the fitting and the tests read it as it is written. */
  var RANGE = /\d\s?\u2013\s?\d/g;
  function textIn(e, text) {
    var s = String(text), at = 0, m;
    RANGE.lastIndex = 0;
    while ((m = RANGE.exec(s))) {
      if (m.index > at) e.appendChild(document.createTextNode(s.slice(at, m.index)));
      e.appendChild(el("span", "bgo-nb", m[0]));
      at = RANGE.lastIndex;
    }
    if (at < s.length) e.appendChild(document.createTextNode(s.slice(at)));
    return e;
  }
  /** A label with a place to break after a "/" between two letters ("Nombre/grupo" on two lines whole: bingo.css
   *  never breaks a label inside a word unless it is wider than its line: fitCards). */
  var LETTER_SLASH = /([A-Za-z0-9\u00c0-\u024f])\/(?=[A-Za-z0-9\u00c0-\u024f])/g;
  function labelText(text) { return String(text).replace(LETTER_SLASH, "$1/\u200b"); }
  /** The head's words (the title, the line under it) into an element, a <wbr> where a long piece of them may break
   *  (GVBingo.headPieces: a pasted link after its "/" and ".", an e-mail after its "@") — the same text, as typed. */
  function headIn(e, text) {
    var parts = CORE.headPieces ? CORE.headPieces(text) : [String(text)];
    e.textContent = "";
    for (var i = 0; i < parts.length; i++) {
      if (i) e.appendChild(document.createElement("wbr"));
      e.appendChild(document.createTextNode(parts[i]));
    }
    return e;
  }
  /** An info square's icon: the mail when it gives our address, the globe for the site's, else the calendar. */
  function infoIcon(text, info) {
    if (info.email && text.indexOf(info.email) >= 0) return "mail";
    if (info.site && text.indexOf(info.site) >= 0) return "globe";
    return "calendar";
  }
  function cellEl(c, info) {
    var d = el("div", "bgo-cell");
    d.setAttribute("role", "listitem");
    d.setAttribute("data-type", c.type);
    d.setAttribute("data-mark", c.mark);
    d.setAttribute("data-pub", c.pub);
    if (c.free) {
      var fm = el("span", "bgo-free-mark");
      fm.setAttribute("aria-hidden", "true");
      var g = icon("free");
      if (g) fm.appendChild(g);
      d.appendChild(fm);
    }
    var box = el("p", "bgo-txt");
    box.appendChild(textIn(el("span", "bgo-w"), breakable(c.text)));
    d.appendChild(box);
    var mk = null;
    if (c.mark === "line") {
      mk = el("span", "bgo-mk");
      mk.appendChild(el("span", "bgo-line"));
      mk.appendChild(el("span", "bgo-lab", labelText(c.label)));
    } else if (c.mark === "box") {
      mk = el("span", "bgo-mk");
      mk.appendChild(el("span", "bgo-lab", labelText(c.label)));
      mk.appendChild(el("span", "bgo-box"));
    } else if (c.mark === "tick") {
      mk = el("span", "bgo-mk");
      mk.appendChild(el("span", "bgo-tick"));
    } else if (c.mark === "icon") {
      mk = el("span", "bgo-mk");
      var ic = el("span", "bgo-ic");
      ic.setAttribute("aria-hidden", "true");
      var svg = icon(infoIcon(c.text, info));
      if (svg) ic.appendChild(svg);
      mk.appendChild(ic);
    }
    if (mk) d.appendChild(mk);
    return d;
  }
  /** "Label: value" in the meetings strip (an address in it breaks where a square's does, a time range stays whole:
   *  breakable, textIn). */
  function infoLine(parent, label, value) {
    if (!value) return;
    var p = el("p", "bgo-li");
    p.appendChild(el("b", "", label + ":"));
    textIn(p, " " + breakable(value));
    parent.appendChild(p);
  }
  /** The forms of the meeting lines bingo.info has, the shortest first: "short", "mid" (short + where), "long". */
  function stripForms(info) {
    var out = [];
    ["Short", "Mid", ""].forEach(function (suf) {
      if (info["gvMeeting" + suf] || info["committeeMeeting" + suf]) out.push(suf ? suf.toLowerCase() : "long");
    });
    return out;
  }
  /** A meeting's line in that form, or the next shorter one there is: { text, long } — or null (no such meeting). */
  function meetingText(info, key, form, L) {
    var order = form === "long" ? ["", "Mid", "Short"] : form === "mid" ? ["Mid", "Short"] : ["Short", "Mid", ""];
    for (var i = 0; i < order.length; i++) {
      var v = info[key + order[i]];
      if (v && v[L]) return { text: v[L], long: order[i] === "" };
    }
    return null;
  }
  /** The meetings strip's words (its heading, the two meetings in that form, how to write to us), in `it`. A small
   *  card's leaves the site's address out (its footer and its QR code give it already: the room goes to the meeting
   *  lines). */
  function fillStrip(it, v, form) {
    var cw = v.cw, info = v.info, L = v.s.lang;
    it.textContent = "";
    it.appendChild(el("p", "bgo-h", cw.info_h));
    [["gvMeeting", cw.gv_meeting, cw.gv_meeting_short], ["committeeMeeting", cw.committee_meeting, cw.committee_short]].forEach(function (m) {
      var t = meetingText(info, m[0], form, L);
      if (t) infoLine(it, t.long ? m[1] : m[2], t.text);
    });
    infoLine(it, cw.write_us, [info.email, v.compact ? "" : info.site].filter(Boolean).join(" · "));
  }
  /**
   * One card → <article class="bgo-card">. card: GVBingo.card()'s; v: the run's view —
   *   { s (the settings), cw (the card words of the card's language), info, dims ({ w, h, k, side }), layout,
   *     sidePx (the side column's width, measured), form (the strip's meeting lines: long | mid | short), head
   *     ({ title, sub }: their sizes in pt when measured smaller, placeCard), compact (a small card — 2 or 4 on a
   *     sheet: the short "How to play"), typedHead (a title or an event typed), title, ev (the event), date,
   *     dateShort, sub (the event · the date, as placeCard chose it: subOf), rules (the "How to play" words) }.
   */
  function buildCard(card, v) {
    var s = v.s, L = card.lang, cw = v.cw, info = v.info;
    var a = el("article", "bgo-card");
    a.lang = L;
    a.setAttribute("data-layout", v.layout);
    a.setAttribute("data-ink", s.color ? "color" : "bw");
    a.setAttribute("data-dense", card.dense ? "1" : "0");
    a.setAttribute("data-compact", v.compact ? "1" : "0");
    a.style.cssText = "--w:" + v.dims.w + "in;--h:" + v.dims.h + "in;--k:" + v.dims.k + ";--rows:" + card.rows +
      ";--cols:" + card.cols + ";--side:" + (v.sidePx ? v.sidePx + "px" : v.dims.side + "in");
    // the head: the grapes, the title, the event and its date
    var head = el("header", "bgo-head");
    var logo = el("span", "bgo-logo");
    logo.setAttribute("aria-hidden", "true");
    var g = icon("grapes");
    if (g) logo.appendChild(g);
    head.appendChild(logo);
    var ht = el("div", "bgo-head-txt");
    var tt = headIn(el("p", "bgo-title"), v.title);
    if (v.head && v.head.title) tt.style.fontSize = v.head.title + "pt";
    ht.appendChild(tt);
    if (v.sub) {
      var sb = headIn(el("p", "bgo-sub"), v.sub);
      if (v.head && v.head.sub) sb.style.fontSize = v.head.sub + "pt";
      ht.appendChild(sb);
    }
    head.appendChild(ht);
    a.appendChild(head);
    if (s.showName) {
      var names = el("div", "bgo-names");
      [cw.name_line, cw.group_line].forEach(function (t) {
        var f = el("p", "bgo-field");
        f.appendChild(el("span", "", t));
        names.appendChild(f);
      });
      a.appendChild(names);
    }
    // the grid, then (beside it or under it) how to play and the meetings strip
    var body = el("div", "bgo-body");
    var gb = el("div", "bgo-gridbox");
    var grid = el("div", "bgo-grid");
    grid.setAttribute("role", "list");
    for (var i = 0; i < card.cells.length; i++) grid.appendChild(cellEl(card.cells[i], info));
    gb.appendChild(grid);
    body.appendChild(gb);
    if (s.showRules || s.showInfo) {
      var side = el("div", "bgo-side");
      if (s.showRules) {
        var r = el("div", "bgo-rules");
        r.appendChild(el("p", "bgo-h", cw.rules_h));
        r.appendChild(el("p", "bgo-rules-txt", v.rules));
        side.appendChild(r);
      }
      if (s.showInfo) {
        var inf = el("div", "bgo-info");
        var it = el("div", "bgo-info-txt");
        fillStrip(it, v, v.form);
        inf.appendChild(it);
        if (info.home && info.home[L] && document.getElementById("bgo-qr-" + L)) {
          var fig = el("figure", "bgo-qr");
          var svg = document.createElementNS(SVG_NS, "svg");
          svg.setAttribute("class", "bgo-qr-svg");
          svg.setAttribute("aria-hidden", "true");
          svg.setAttribute("focusable", "false");
          var use = document.createElementNS(SVG_NS, "use");
          use.setAttribute("href", "#bgo-qr-" + L);
          svg.appendChild(use);
          fig.appendChild(svg);
          fig.appendChild(el("figcaption", "", cw.qr));
          inf.appendChild(fig);
        }
        side.appendChild(inf);
      }
      body.appendChild(side);
    }
    a.appendChild(body);
    var foot = el("footer", "bgo-foot");
    foot.appendChild(el("p", "bgo-anon", cw.anon));
    foot.appendChild(el("p", "bgo-meta", fmt(cw.foot, { n: card.index + 1, total: s.count, code: card.code }) + (info.site ? " · " + info.site : "")));
    a.appendChild(foot);
    return a;
  }

  /** The dashed cut lines between the n cards of a sheet (inside its margin, --m): only between two cards — a part-full
   *  last sheet gets none across its empty places. */
  function cutLines(sheet, dims, n) {
    var sh = dims.sheet, m = sh.margin, w = dims.w, h = dims.h, g = sh.gap;
    var full = Math.floor(n / sh.across);                  // the rows with every place taken
    if (sh.across > 1 && full > 0) {
      var cv = el("span", "bgo-cut bgo-cut-v");
      cv.style.cssText = "left:" + r3(m + w + g / 2) + "in;top:" + m + "in;height:" + r3(full * h + (full - 1) * g) + "in";
      sheet.appendChild(cv);
    }
    if (sh.down > 1 && n > sh.across) {
      var ch = el("span", "bgo-cut bgo-cut-h");
      var wide = n - sh.across >= sh.across ? sh.across : n - sh.across;   // the places taken in the row under it
      ch.style.cssText = "top:" + r3(m + h + g / 2) + "in;left:" + m + "in;width:" + r3(wide * w + (wide - 1) * g) + "in";
      sheet.appendChild(ch);
    }
  }

  /* ---------------- the layout of a card: "stack" (every part across the card, one under the other), "side" (the
     grid the whole height, the head and the rest in a column beside it) or "top" (the head and the name lines
     across the top, the grid and the column under them): bingo.css — "side" or "top" only when the squares come
     out 5 % bigger so (a wide card: landscape, two on a portrait sheet) and the column fits, nothing over the small
     print ---------------- */
  // The side column's width: what the grid cannot use (its squares are as tall as the card lets them be: the grid
  // needs cols × that), never narrower than the core's SIDE in × the card's scale; when its parts are taller than
  // the column at that width (a small card), wider in steps — up to 55 % of the card — until they fit.
  /** Nothing sticks out: not the card's parts out of the card, not the side column's parts over the small print. */
  function fitsCard(a) {
    var sd = a.querySelector(".bgo-side");
    return a.scrollHeight <= a.clientHeight + 1 && (!sd || sd.scrollHeight <= sd.clientHeight + 1);
  }
  /** How whole the head's words are as laid out: 2 no word of the title or of the line under it is wider than its line
   *  (in a narrow side column a long typed word would break in two, "Compañerism" / "o"; a <wbr> is a place to break:
   *  headIn), 1 the title's only, 0 not even those — measured with the words kept whole for a moment. */
  function wholeOf(a) {
    var hs = [a.querySelector(".bgo-title"), a.querySelector(".bgo-sub")], ok = [];
    hs.forEach(function (e) { if (e) e.style.overflowWrap = "normal"; });
    hs.forEach(function (e) { ok.push(!e || e.scrollWidth <= e.clientWidth + 1); });
    hs.forEach(function (e) { if (e) e.style.overflowWrap = ""; });
    return ok[0] ? (ok[1] ? 2 : 1) : 0;
  }
  /** The card as layout lay ({ layout, side }); hd (a smaller head step, placeIn: { f, base }): the head's words at
   *  f × that layout's own sizes (sizeHead) → those sizes. */
  function setLayout(a, lay, dims, hd) {
    var side = lay.side ? lay.side + "px" : dims.side + "in";
    setAttr(a, "data-layout", lay.layout);
    if (a.style.getPropertyValue("--side") !== side) a.style.setProperty("--side", side);
    return hd ? sizeHead(a, hd, lay.layout) : { title: "", sub: "" };
  }
  /** The side column's widths for layout `name` ("side" or "top"), the narrowest first, in steps of 5 % of the card
   *  (cell: a square, measured at each) → { first: the narrowest where nothing sticks out (0: none), firstCell (px),
   *  firstWhole (wholeOf there), and use, useCell, useWhole: the narrowest where more of the head's words are whole
   *  (all of them, else the title's; else first) — but never a width whose squares are smaller than least px (0:
   *  WHOLE_COST under first's) }. */
  function widths(a, card, dims, name, cell, gb, hd, least) {
    setLayout(a, { layout: name, side: 0 }, dims, hd);
    var minPx = dims.side * PX_IN, gap = parseFloat(getComputedStyle(a).columnGap) || 0;
    var total = gb.offsetWidth + minPx + gap, room = gb.clientHeight;
    var gridW = card.cols * (room / card.rows) + 6;
    var most = total * 0.55, w = { first: 0, firstCell: 0, firstWhole: 0, use: 0, useCell: 0, useWhole: 0 };
    for (var side = clamp(total - gap - gridW, minPx, most); side <= most + 0.5; side += Math.max(8, total * 0.05)) {
      a.style.setProperty("--side", Math.round(side) + "px");
      if (!fitsCard(a)) continue;
      var px = cell.offsetWidth, at = Math.round(side);
      if (!w.first) {
        w.first = at;
        w.firstCell = px;
        if (!least) least = px * (1 - WHOLE_COST);
      }
      if (px < least) break;                  // (wider costs the squares too much)
      var lvl = wholeOf(a);
      if (at === w.first) w.firstWhole = lvl;
      if (!w.use || lvl > w.useWhole) {
        w.use = at;
        w.useCell = px;
        w.useWhole = lvl;
      }
      if (lvl === 2) break;
    }
    return w;
  }
  // "side" first; "top" (the head and the name lines across the top) when the side column cannot hold them too: at
  // the narrowest width where nothing sticks out (widths) → { layout, side, cell (px), alt }. alt (or null): another
  // layout — a wider column, the other one, or "stack" (the head across the whole card) — that keeps more of the
  // head's words whole (a long word breaks in two in a narrow column: "Compañerism" / "o"), offered only when its
  // squares are no more than WHOLE_COST smaller (the most whole, then the biggest squares); placeCard takes it only
  // when no more squares miss THE FLOOR there. A long piece with places to break (a pasted link: GVBingo.headPieces)
  // breaks there at the narrow width; one with none (a made-up word of 45 letters) breaks anywhere — a wider column
  // never costs the squares more.
  function chooseLayout(a, card, dims, hd) {
    var cell = a.querySelector(".bgo-cell"), gb = a.querySelector(".bgo-gridbox");
    var stack = { layout: "stack", side: 0, cell: 0, alt: null };
    setLayout(a, stack, dims, hd);
    if (!cell || !gb) return stack;
    stack.cell = cell.offsetWidth;
    // (no column beside the grid can make its squares 5 % bigger when even the narrowest one leaves them smaller: a
    // tall card, a wide grid — nothing to try)
    if ((gb.clientWidth - dims.side * PX_IN) / card.cols <= stack.cell * 1.05) return stack;
    var narrow = null, best = null;
    ["side", "top"].forEach(function (name) {
      if (narrow && best && best.whole === 2) return;
      var w = widths(a, card, dims, name, cell, gb, hd, narrow ? narrow.cell * (1 - WHOLE_COST) : 0);
      if (!narrow && w.first && w.firstCell > stack.cell * 1.05) {
        narrow = { layout: name, side: w.first, cell: w.firstCell, whole: w.firstWhole };
      }
      var more = !best || w.useWhole > best.whole || (w.useWhole === best.whole && w.useCell > best.cell);
      if (w.use && w.useCell > stack.cell * 1.05 && more) best = { layout: name, side: w.use, cell: w.useCell, whole: w.useWhole };
    });
    if (!narrow) { setLayout(a, stack, dims, hd); return stack; }
    if (narrow.whole < 2 && (!best || best.whole < 2) && stack.cell >= narrow.cell * (1 - WHOLE_COST)) {
      setLayout(a, stack, dims, hd);
      var lvl = wholeOf(a);
      if (!best || lvl > best.whole) best = { layout: "stack", side: 0, cell: stack.cell, whole: lvl };
    }
    var out = { layout: narrow.layout, side: narrow.side, cell: narrow.cell, alt: null };
    if (best && best.whole > narrow.whole && best.cell >= narrow.cell * (1 - WHOLE_COST)) {
      out.alt = { layout: best.layout, side: best.side };
    }
    setLayout(a, out, dims, hd);
    return out;
  }
  /** The head's sizes as the stylesheet has them in each layout ("side" has a smaller title), in pt: { stack: { title,
   *  sub }, side, top } — measured once a run (placeIn), so a smaller head step is the same size whatever was tried
   *  before it. */
  function headBase(a) {
    var was = a.getAttribute("data-layout"), out = {};
    var t = a.querySelector(".bgo-title"), s = a.querySelector(".bgo-sub");
    if (t) t.style.fontSize = "";
    if (s) s.style.fontSize = "";
    var pt = function (e) { return e ? parseFloat(getComputedStyle(e).fontSize) * 0.75 : 0; };
    ["stack", "side", "top"].forEach(function (lay) {
      a.setAttribute("data-layout", lay);
      out[lay] = { title: pt(t), sub: pt(s) };
    });
    a.setAttribute("data-layout", was);
    return out;
  }
  /** The head's words at hd.f × layout's own sizes (hd.base: headBase), never under 8pt (the title) and 6pt (the event
   *  and the date) → { title, sub }: the sizes set, in pt. */
  function sizeHead(a, hd, layout) {
    var b = hd.base[layout] || hd.base.stack, out = { title: "", sub: "" };
    [["title", ".bgo-title", 8], ["sub", ".bgo-sub", 6]].forEach(function (h) {
      var e = a.querySelector(h[1]);
      if (!e || !b[h[0]]) return;
      var pt = Math.max(h[2], Math.floor(b[h[0]] * hd.f * 2) / 2);
      if (e.style.fontSize !== pt + "pt") e.style.fontSize = pt + "pt";
      out[h[0]] = pt;
    });
    return out;
  }
  /** A square's side as laid out, in px (unscaled: the preview's transform is not in it; not rounded). */
  function cellW(a) {
    var c = a.querySelector(".bgo-cell");
    return c ? parseFloat(getComputedStyle(c).width) || c.offsetWidth : 0;
  }
  /** The short words: a big grid, or squares smaller than SMALL_CELL as drawn (px; 0: none measured, the core's
   *  estimate). */
  function denseAt(card, px) {
    return card.rows >= DENSE || card.cols >= DENSE || (px > 0 ? px / PX_IN < SMALL_CELL : card.dense);
  }
  /** The head's steps this card may take (HEAD_STEPS). */
  function headSteps(v) { return v.typedHead ? HEAD_STEPS : HEAD_STEPS.slice(0, v.compact ? 2 : 1); }
  /** The line under the title: the event · the date, in the step's form (HEAD_STEPS). */
  function subOf(v, date) {
    if (date === "none" && v.ev) return v.ev;
    var d = date === "long" ? v.date : v.dateShort;
    return v.ev && d ? v.ev + " · " + d : v.ev || d;
  }
  /** THE FLOOR (LAYOUT): how many of these squares (cells: every square the run may draw, each once) would print under
   *  MIN_PT at a square of px pixels — measured in a hidden grid of them inside the card's grid box (.bgo-probe: the
   *  card's own look, dense or not, its marks and labels), their words at MIN_PT with breaks allowed (as fitCards
   *  allows them there). A miss: words taller than their box, a box with no height at all (its mark and label took
   *  the whole square: the probe is always laid out, so that is no room, not "not measured" as fitsNow reads it), or
   *  a label wider than its line. A square measured before (store, M.floor: its record, floorRec) is not laid out
   *  again when that tells already — one that fit at a smaller size fits, one that missed at a bigger size misses (a
   *  bigger square has more room for the same words) —, and the likeliest to miss are measured first: once more than
   *  `bar` miss, the count stops there (a number above bar, not kept). keep (the run's: draw, M.keep): the counts of
   *  each square size, and the run's records. */
  function floorMisses(a, cells, info, dense, px, keep, bar, store) {
    var gb = a.querySelector(".bgo-gridbox");
    if (!gb || !px || !cells || !cells.length) return 0;
    var at = (dense ? "d" : "f") + Math.round(px * 100);
    if (keep[at] != null) return keep[at];
    var k = dense ? "dense" : "full", R = keep[k], i, n = 0, todo = [], seen = false;
    if (!R) R = keep[k] = cells.map(function (c) { return floorRec(store, c, info, dense); });
    for (i = 0; i < R.length; i++) {
      if (px >= R[i].hi) continue;
      if (px <= R[i].lo) n++;
      else {
        todo.push(i);
        if (R[i].lo) seen = true;
      }
    }
    // (when some of them missed at a smaller size: the ones that missed nearest this size first, then the longest
    // words, FLOOR_FIRST of them, then the rest)
    var few = todo.length;
    if (seen) {
      todo.sort(function (x, y) { return R[y].lo - R[x].lo || R[y].len - R[x].len || x - y; });
      few = FLOOR_FIRST;
    }
    var probe = store.probe, cols = Math.max(1, Math.floor(gb.clientWidth / px)), was = a.getAttribute("data-dense");
    setAttr(a, "data-dense", dense ? "1" : "0");
    for (var from = 0; from < todo.length && !(n > bar); ) {
      var to = from ? todo.length : Math.min(todo.length, few);
      for (i = from; i < to; i++) probe.appendChild(R[todo[i]].el);
      probe.style.cssText = "--c:" + px + "px;--cols:" + cols;
      gb.appendChild(probe);
      for (i = from; i < to; i++) {
        var r = R[todo[i]], lab = r.el.querySelector(".bgo-lab"), tx = r.el.querySelector(".bgo-txt");
        // (a words' box with no height at all: the mark and its label took the whole square — a miss, never a fit)
        if (!tx.clientHeight || !fitsNow(r.el.querySelector(".bgo-w"), tx) || (lab && lab.scrollWidth > lab.clientWidth + 1)) {
          n++;
          r.lo = px;
        } else {
          r.hi = px;
        }
      }
      gb.removeChild(probe);
      probe.textContent = "";
      from = to;
    }
    setAttr(a, "data-dense", was);
    if (from < todo.length) return n;
    keep[at] = n;
    return n;
  }
  /** A square's record in the floor's store (floorMisses): its element in the probe (its words at MIN_PT, breaks
   *  allowed), lo — the biggest size (px) it missed at so far —, hi — the smallest it fit at —, and its length. The
   *  same words, mark and label, with the short words' look or not, have one record, whatever the run. */
  function floorRec(store, c, info, dense) {
    var key = [dense ? "d" : "f", c.type, c.mark, c.pub, c.text, c.label].join("\u0001"), r = store.recs[key];
    if (!r) {
      var e = cellEl(c, info);
      setPt(e.querySelector(".bgo-w"), MIN_PT, true);
      r = store.recs[key] = { el: e, lo: 0, hi: Infinity, len: e.textContent.length };
      store.n++;
    }
    return r;
  }
  /** What else may change how the page draws text (the floor's store is emptied when it changes): the attributes of
   *  <html> (the site's own reading settings, the theme), the screen's pixel ratio (the browser's zoom). */
  function pageLook() {
    var r = document.documentElement, out = [window.devicePixelRatio || 1];
    for (var i = 0; i < r.attributes.length; i++) out.push(r.attributes[i].name + "=" + r.attributes[i].value);
    return out.join(" ");
  }
  /** The run's layout, measured on one card (`a`, in the page; LAYOUT, in the header): head step by head step, the
   *  strip forms that say where we meet from the longest ("long" against "mid": LONG_COST), then the "short" lines
   *  the same way, each laid out (chooseLayout) and measured (missesOf(a, dense, px, bar): THE FLOOR) until one keeps
   *  the floor — no more misses than the shortest lines with the last head step at the narrowest layout, nothing
   *  sticking out. A form is tried at the last head step first, once (no step helps a form that misses there). A
   *  smaller head step's words are that step's share of the stylesheet's size in the layout tried (headBase,
   *  sizeHead). Left in `a` → { layout, side, form, step, sub, head: { title, sub }, cellIn, dense, … }. Meanwhile the
   *  card's squares are empty (.is-placing: their words do not change the grid's size, and a card of 100 words is
   *  slow to lay out again and again). */
  function placeCard(a, card, dims, v, missesOf) {
    a.classList.add("is-placing");
    try { return placeIn(a, card, dims, v, missesOf); } finally { a.classList.remove("is-placing"); }
  }
  function placeIn(a, card, dims, v, missesOf) {
    var sb = a.querySelector(".bgo-sub"), it = a.querySelector(".bgo-info-txt");
    var forms = it ? stripForms(v.info) : [];
    if (!forms.length) forms = [""];
    var steps = headSteps(v), last = steps.length - 1, memo = {}, at = "", bases = null, stripAt = null;
    // the card's words as form fi and head step si: the line under the title, the strip's lines, the head's size → hd
    // for a smaller head step ({ f, base }: setLayout), else null (the stylesheet's sizes)
    function words(fi, si) {
      var sub = subOf(v, steps[si][0]);
      if (sb && sb.textContent !== sub) headIn(sb, sub);
      if (it && stripAt !== forms[fi]) fillStrip(it, v, stripAt = forms[fi]);
      var f = steps[si][1];
      if (f < 1) return { f: f, base: bases || (bases = headBase(a)) };
      [".bgo-title", ".bgo-sub"].forEach(function (q) { var e = a.querySelector(q); if (e && e.style.fontSize) e.style.fontSize = ""; });
      return null;
    }
    // a layout of these words set and measured: the record placeCard returns (its floor counted when asked: misses)
    function measure(fi, si, lay, hd) {
      var head = setLayout(a, lay, dims, hd), px = cellW(a), dense = denseAt(card, px);
      setAttr(a, "data-dense", dense ? "1" : "0");
      return { layout: lay.layout, side: lay.side, form: forms[fi], step: si, sub: subOf(v, steps[si][0]), head: head, px: px,
               cellIn: px / PX_IN, dense: dense, fits: fitsCard(a), misses: null };
    }
    // (a trial's floor count: exact when it is bar or less — or with no bar —, else some number above bar)
    function misses(t, bar) {
      if (t.misses != null) return t.misses;
      var n = missesOf(a, t.dense, t.px, bar);
      if (bar == null || n <= bar) t.misses = n;
      return n;
    }
    function again(t, hd) {
      setLayout(a, t, dims, hd);
      setAttr(a, "data-dense", t.dense ? "1" : "0");
    }
    // the card as form fi and head step si, laid out (chooseLayout: its narrowest layout, or the one that keeps more
    // of the head's words whole when no more squares miss the floor there) — measured once each: a step tried again
    // is only set again. memo: { use, narrow }
    function put(fi, si) {
      var key = fi + ":" + si, m = memo[key];
      if (at === key) return m.use;
      at = key;
      var hd = words(fi, si);
      if (m) { again(m.use, hd); return m.use; }
      var lay = chooseLayout(a, card, dims, hd), n = measure(fi, si, lay, hd), use = n;
      if (lay.alt) {
        var w = measure(fi, si, lay.alt, hd);
        if (w.fits && (!misses(w, 0) || misses(w, misses(n)) <= misses(n))) use = w;
        else again(n, hd);
      }
      memo[key] = { use: use, narrow: n };
      return use;
    }
    // (the base — the shortest lines, the last head step, at the narrowest layout: a miss a wider column causes is
    // never the bar — measured only when a trial misses: no miss, no doubt)
    var base = null, pick = null;
    function holds(fi, si) {
      var t = put(fi, si);
      if (!t.fits) return false;
      if (!misses(t, 0)) return true;
      if (!base) {
        put(0, last);
        base = memo["0:" + last].narrow;
      }
      return misses(t, misses(base)) <= misses(base);
    }
    // (a form that does not hold at the last head step holds at none: the smallest head leaves the squares the most
    // room. Tried there first, once: that trial's floor is mostly known already — THE FLOOR's store —, while a form
    // tried at step 0 first and missing there would take one more layout)
    var dead = {};
    function can(fi, si) {
      if (dead[fi] == null) dead[fi] = !holds(fi, last);
      return !dead[fi] && holds(fi, si);
    }
    // the forms that say where we meet: all but "short" (none when it is the only one)
    var place = forms.length > 1 && forms[0] === "short" ? 1 : 0, fi, si;
    for (si = 0; si <= last && !pick; si++) {
      for (fi = forms.length - 1; fi >= place && !pick; fi--) {
        if (!can(fi, si)) continue;
        pick = [fi, si];
        // "long" only while its squares stay within LONG_COST of the "mid" lines' at this step (their size first: the
        // floor only when it matters)
        if (forms[fi] === "long" && forms[fi - 1] === "mid" &&
            put(fi, si).cellIn < put(fi - 1, si).cellIn * (1 - LONG_COST) && holds(fi - 1, si)) pick = [fi - 1, si];
      }
    }
    for (si = 0; place && si <= last && !pick; si++) if (can(0, si)) pick = [0, si];
    return pick ? put(pick[0], pick[1]) : put(0, last);
  }

  /* ---------------- the text fitting (the header says how) ---------------- */
  // the sizes to try: up to 0.19 × the square (the core's fontGuess, which cannot measure, starts lower: 0.17 ×)
  function sizesFor(mark, cellPx, most) {
    var inch = cellPx / PX_IN;
    var top = mark === "free" ? clamp(inch * 72 * 0.3, 9, 36) : clamp(inch * 72 * 0.19, 8, 20);
    if (most) top = Math.min(top, most);
    var out = [];
    for (var f = MIN_FIT; f <= top + 1e-6; f += 0.5) out.push(f);
    return out;
  }
  /** A size, and whether words may break at it (hy: hyphens, and a word too long for the line breaks anywhere). */
  function setPt(w, pt, hy) {
    w.style.fontSize = pt + "pt";
    if (hy) w.classList.add("is-hy"); else w.classList.remove("is-hy");
  }
  /** The batched binary search: for every group the biggest of its sizes that fits (-1: none), hy as given. */
  function search(groups, hy) {
    groups.forEach(function (g) { g.lo = -1; g.hi = g.sizes.length - 1; });
    var active = groups.slice(), rounds = 0;
    while (active.length && rounds++ < 12) {
      active.forEach(function (g) { g.mid = Math.ceil((g.lo + g.hi) / 2); setPt(g.w, g.sizes[Math.max(0, g.mid)], hy); });
      active.forEach(function (g) { if (fitsNow(g.w, g.box)) g.lo = g.mid; else g.hi = g.mid - 1; });
      active = active.filter(function (g) { return g.lo < g.hi; });
    }
    groups.forEach(function (g) { g.found = g.lo >= 0 ? g.sizes[g.lo] : 0; });
  }
  function fitsNow(w, box) {
    var bh = box.clientHeight;
    if (!bh) return true;                       // not laid out (hidden): nothing to measure
    if (w.offsetHeight > bh - 1) return false;
    return w.classList.contains("is-hy") || w.scrollWidth <= w.clientWidth;
  }
  function median(a) {
    if (!a.length) return 0;
    var b = a.slice().sort(function (x, y) { return x - y; });
    return b[Math.floor((b.length - 1) / 2)];
  }
  /** Fit the words of every square of these cards (one run: the same settings, the same size of square). */
  function fitCards(cards) {
    var groups = {}, list = [], perCard = [], labs = [];
    // (a fitting again starts clean: no thin line, no label broken inside a word)
    cards.forEach(function (a) {
      var cells = a.querySelectorAll(".bgo-cell");
      for (var i = 0; i < cells.length; i++) {
        cells[i].classList.remove("is-tight");
        var lb = cells[i].querySelector(".bgo-lab");
        if (lb) { lb.classList.remove("is-hy"); labs.push(lb); }
      }
    });
    // a label wider than its line (one long word in a small square) breaks inside the word, never cut off — first:
    // its lines are part of the room its words get
    labs.filter(function (lb) { return lb.scrollWidth > lb.clientWidth + 1; }).forEach(function (lb) { lb.classList.add("is-hy"); });
    cards.forEach(function (a, ci) {
      var cells = a.querySelectorAll(".bgo-cell"), mine = [];
      for (var i = 0; i < cells.length; i++) {
        var cell = cells[i], w = cell.querySelector(".bgo-w"), box = cell.querySelector(".bgo-txt");
        if (!w || !box) continue;
        var lab = cell.querySelector(".bgo-lab");
        var mark = cell.getAttribute("data-mark");
        var key = mark + "\u0001" + w.textContent + "\u0001" + (lab ? lab.textContent : "");
        var g = groups[key];
        if (!g) {
          g = groups[key] = { mark: mark, w: w, box: box, cell: cell, pt: 0 };
          list.push(g);
        }
        mine.push({ g: g, w: w, box: box, free: mark === "free" });
      }
      perCard[ci] = mine;
    });
    if (!list.length) return;
    var cellPx = list[0].cell.offsetWidth || PX_IN;
    // 1. whole words: the biggest size at which no word is cut (6 pt or more: done)
    list.forEach(function (g) { g.sizes = sizesFor(g.mark, cellPx); });
    search(list, false);
    list.forEach(function (g) { g.pt = g.found; g.hy = false; });
    // 2. the rest (a word too long for the square even at 6 pt): words may break, at HY_AT pt or less
    var tight = list.filter(function (g) { return g.found < MIN_PT; });
    if (tight.length) {
      tight.forEach(function (g) { g.sizes = sizesFor(g.mark, cellPx, HY_AT); });
      search(tight, true);
      tight.forEach(function (g) {
        if (g.found > g.pt) { g.pt = g.found; g.hy = true; }
        if (!g.pt) { g.pt = MIN_FIT; g.hy = true; }
      });
    }
    // card by card: one middle size, the rest kept near it; then every square gets its size
    var all = [];
    perCard.forEach(function (mine) {
      var m = median(mine.filter(function (x) { return !x.free; }).map(function (x) { return x.g.pt; }));
      var cap = m ? Math.max(MIN_FIT, Math.floor(m * HARMONY * 2) / 2) : 99;
      mine.forEach(function (x) {
        var pt = x.free ? Math.min(x.g.pt, Math.max(cap * 1.6, 9)) : Math.min(x.g.pt, cap);
        x.pt = Math.floor(pt * 2) / 2;
        x.hy = x.g.hy;
        setPt(x.w, x.pt, x.hy);
        all.push(x);
      });
    });
    // the last check: anything that still sticks out shrinks (rarely anything: the same words measured the same)
    for (var pass = 0; pass < 4; pass++) {
      var bad = all.filter(function (x) { return x.pt > MIN_FIT && !fitsNow(x.w, x.box); });
      if (!bad.length) break;
      bad.forEach(function (x) { x.pt -= 0.5; setPt(x.w, x.pt, x.hy); });
    }
    // the last resort: words that do not fit even at MIN_FIT (a CSV row too long for squares this small) take the
    // room of their write-in line (bingo.css .is-tight: a thin line) — never cut off
    all.forEach(function (x) { if (!fitsNow(x.w, x.box)) x.box.parentNode.classList.add("is-tight"); });
  }

  /* ---------------- the component ---------------- */
  document.addEventListener("alpine:init", function () {
    var Alpine = window.Alpine;

    Alpine.data("bingoBuilder", function (pageLang) {
      // outside Alpine's reactivity: the page's data, the core, the squares' ids the page has, the memo of the pool,
      // the pick list, the run's squares and the floor's counts (THE FLOOR: keepKey, the settings and the fonts they
      // were measured with), timers (and the print run under way, which settings the sheets were made for, how many
      // times the fonts came in)
      var G = null, D = null, base = null, KNOWN = null;
      var M = { rev: -1, pool: null, counts: null, pickKey: "", pick: null, cellsRev: -1, cells: {}, keepKey: "", keep: {}, floor: null };
      var T = { save: 0, draw: 0, typed: 0, job: null, printed: -1, hidden: false, ro: 0, fonts: 0 };
      var L = pageLang === "es" ? "es" : "en";
      /** The settings without the squares and categories this page does not have (from a link or a memory older than
       *  the CSV: "4 chosen by hand" for squares that are not there, and a link that grows with every change). */
      function onlyKnown(s) {
        ["pick", "pin"].forEach(function (k) {
          Object.keys(s[k] || {}).forEach(function (id) { if (!Object.prototype.hasOwnProperty.call(KNOWN, id)) delete s[k][id]; });
        });
        Object.keys(s.cats || {}).forEach(function (c) { if ((D.cats || []).indexOf(c) < 0) delete s.cats[c]; });
        return s;
      }

      return {
        ready: false,
        broken: false,
        rev: 0,
        s: {},
        idx: 0,
        custom: false,
        pickOpen: false,
        openCats: {},     // the kinds of squares opened in "Choose squares yourself" ({ <cat>: true })
        q: "",
        codeDraft: "",
        codeErr: false,
        busy: false,
        done: 0,
        asking: false,    // "Start over?" shown
        zoom: false,      // the preview at its paper size ("Actual size")
        fitK: 1,          // the preview's scale to fit its column
        // what the preview measured (LAYOUT): the run's layout, side column, strip lines, head (its step, the line
        // under the title, its sizes), short words, square size
        layout: "stack",
        sidePx: 0,
        form: "",
        headStep: 0,
        sub: "",
        head: null,
        dense: false,
        cellIn: 0,

        /* ================= start-up ================= */
        init: function () {
          var self = this;
          try {
            D = JSON.parse(document.getElementById("bingo-data").textContent);
          } catch (e) { D = null; }
          G = window.GVBingo;
          if (!D || !G || typeof G.normalize !== "function" || !Array.isArray(D.items)) { this.broken = true; return; }
          KNOWN = Object.create(null);
          D.items.forEach(function (it) { if (it && typeof it.id === "string") KNOWN[it.id] = 1; });
          base = { lang: L };
          var today = todayCentral();
          var s = G.fromHash(location.hash, base), fromLink = !!s;
          if (!s) {
            var saved = null;
            try { saved = JSON.parse(lsGet(KEY) || "null"); } catch (e) { saved = null; }
            if (saved && saved.s && typeof saved.s === "object") {
              var raw = saved.s;
              if (saved.page !== L) { raw = clone(raw); raw.lang = L; }
              s = G.normalize(raw, base);
              if (s.date && s.date < today) s.date = today;
            } else {
              s = G.normalize({}, base);
            }
          }
          var drew = !s.code;
          if (drew) s.code = G.newCode();
          if (!s.date) s.date = today;
          this.s = onlyKnown(G.normalize(s, base));
          this.custom = this.s.rows !== this.s.cols;
          this.codeDraft = this.s.code;
          this.ready = true;
          this.changed(true);
          // a first visit: its code kept at once (a reload makes the same cards); a link's lives in the address
          if (drew && !fromLink) this.save();
          // a link pasted into this tab's address (a #hash only: no reload)
          window.addEventListener("hashchange", function () {
            var n = G.fromHash(location.hash, base);
            if (!n) return;
            if (!n.code) n.code = self.s.code;
            if (!n.date) n.date = todayCentral();
            self.idx = 0;
            self.custom = n.rows !== n.cols;
            self.apply(n);
          });
          // the browser's own Print (Ctrl+P, the menu): the cards, fitted, before it takes its picture — again when
          // the settings changed since the last sheets were made (a print whose afterprint never came)
          window.addEventListener("beforeprint", function () {
            self.flushTyped();
            if (document.documentElement.getAttribute("data-print") !== "bingo" || T.printed !== self.rev) self.prepare();
          });
          window.addEventListener("afterprint", function () { self.cleanup(); });
          // the preview's scale follows its column (the window, the text size) and what is above it in the column (a
          // help opened, "Start over?" asked) — and a preview that could not be drawn while hidden is drawn now; in
          // the next frame (scale sets the height of the very stage it watches: a change in the observer's own
          // callback is "ResizeObserver loop completed with undelivered notifications" in Safari)
          var later = window.requestAnimationFrame ? function (f) { return window.requestAnimationFrame(f); } : function (f) { return setTimeout(f, 16); };
          var resized = function () {
            if (T.ro) return;
            T.ro = later(function () { T.ro = 0; if (T.hidden) self.queueDraw(); else self.scale(); });
          };
          if (window.ResizeObserver && this.$refs.stage) {
            var ro = new ResizeObserver(resized);
            ro.observe(this.$refs.stage);
            if (this.$refs.preview) ro.observe(this.$refs.preview);
          } else {
            window.addEventListener("resize", resized);
          }
          // the fonts: measured again once they are in (until then the fallback's sizes; the floor's counts too)
          try {
            if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { T.fonts++; self.draw(); });
            if (document.fonts && document.fonts.addEventListener) document.fonts.addEventListener("loadingdone", function () { T.fonts++; self.queueDraw(); });
          } catch (e) { /* no font loading API: the first drawing stays */ }
        },

        /* ================= the settings ================= */
        /** One setting changed (normalized: a wrong value never gets in). A typed one (TYPED) is in the settings at
         *  once, its preview, memory and link TYPE_WAIT ms after the last key. */
        set: function (k, v) {
          var self = this;
          var raw = clone(this.s);
          raw[k] = v;
          if (!TYPED[k]) { this.apply(raw); return; }
          this.s = onlyKnown(G.normalize(raw, base));
          clearTimeout(T.typed);
          T.typed = setTimeout(function () { T.typed = 0; self.changed(false); }, TYPE_WAIT);
        },
        /** A typed change still waiting: done now (before a print, a link, the memory). */
        flushTyped: function () {
          if (!T.typed) return;
          clearTimeout(T.typed);
          T.typed = 0;
          this.changed(false);
        },
        apply: function (raw) {
          this.s = onlyKnown(G.normalize(raw, base));
          this.changed(false);
        },
        changed: function (first) {
          var self = this;
          clearTimeout(T.typed);   // (a typed change waiting is part of this one)
          T.typed = 0;
          this.rev++;
          this.idx = clamp(this.idx, 0, Math.max(0, this.s.count - 1));
          if (document.activeElement !== document.getElementById("bgo-code")) { this.codeDraft = this.s.code; this.codeErr = false; }
          if (!first) {
            clearTimeout(T.save);
            T.save = setTimeout(function () { self.save(); }, 250);
          }
          // a link in the address follows the settings (no new history entry)
          if (this.linkInAddress()) {
            try { history.replaceState(null, "", location.pathname + location.search + G.encode(this.s)); } catch (e) { /* file:// */ }
          }
          this.queueDraw();
        },
        save: function () {
          lsSet(KEY, JSON.stringify({ v: 1, page: L, s: this.s }));
        },
        linkInAddress: function () {
          var h = location.hash || "";
          return h.length > 1 && Object.keys(G.decode(h)).length > 0;
        },
        // the words: the builder's, in the page's language — src/_i18n/bingo.json ("bingo.ui." + k) — and the card's, in
        // the card's language — ("bingo.card." + k) —, handed over by the page without their prefix (#bingo-data:
        // "bingo.ui." | tGroup(lang), the card's in both languages)
        ui: function (k, vars) { return fmt((D && D.ui && D.ui[k]) || "", vars); },
        cw: function () { return (D && D.card && D.card[this.s.lang]) || {}; },
        defaultRules: function (compact) {
          var cw = this.cw(), sq = this.s.rows === this.s.cols;
          return fmt(compact ? (sq ? cw.rules_square_short : cw.rules_rect_short) : (sq ? cw.rules_square : cw.rules_rect), { n: this.s.rows });
        },
        /** A typed "How to play" too long for these small cards: they print the short one (the help line says so). */
        rulesCut: function () {
          return String(this.s.rules || "").trim().length > RULES_COMPACT_MAX && this.compactNow();
        },
        /** The preview's squares leave little room to write (the help line under the grid says what to choose). */
        smallSquares: function () { return this.cellIn > 0 && this.cellIn < SMALL_WRITE; },
        /** A typed title or event the card prints in smaller letters (and with a short date, or none) to keep its
         *  squares at 6 pt (HEAD_STEPS from the third: the help line under the Event box says so — not for a short
         *  date alone, which a small card takes with nothing typed too). */
        headCut: function () {
          var st = HEAD_STEPS[this.headStep];
          return !!st && (st[1] < 1 || st[0] === "none") && !!(String(this.s.title || "").trim() || String(this.s.event || "").trim());
        },
        setDate: function (v) {
          var d = G.normalize({ date: v }).date;
          this.set("date", d || this.s.date || todayCentral());
          if (!d) { var inp = document.getElementById("bgo-date"); if (inp) inp.value = this.s.date; }
        },
        // the grid
        isPreset: function (n) { return !this.customOpen() && this.s.rows === n && this.s.cols === n; },
        preset: function (n) {
          this.custom = false;
          var raw = clone(this.s);
          raw.rows = n;
          raw.cols = n;
          this.apply(raw);
        },
        customOpen: function () { return this.custom || this.s.rows !== this.s.cols; },
        toggleCustom: function () {
          if (this.s.rows !== this.s.cols) { this.custom = true; return; }
          this.custom = !this.custom;
        },
        oddGrid: function () { return this.s.rows % 2 === 1 && this.s.cols % 2 === 1; },
        freeOn: function () { return G ? G.freeOn(this.s) : false; },
        squaresLine: function () {
          if (!G) return "";
          return this.ui(this.freeOn() ? "squares_free" : "squares_n", { n: G.needOf(this.s) });
        },
        // the squares
        P: function () {
          var rev = this.rev;
          if (!G || !D) return { ok: false, have: 0, need: 0, pool: [] };   // (the builder could not start)
          if (M.rev !== rev || !M.pool) {
            M.rev = rev;
            M.pool = G.pool(D.items, this.s);
            M.counts = G.catCounts(D.items, this.s);
          }
          return M.pool;
        },
        catOn: function (c) { return (this.s.cats || {})[c] !== false; },
        catN: function (c) { this.P(); return (M.counts && M.counts[c]) || 0; },
        toggleCat: function (c) {
          var cats = clone(this.s.cats);
          if (cats[c] === false) delete cats[c]; else cats[c] = false;
          this.set("cats", cats);
        },
        poolLine: function () { var p = this.P(); return this.ui(p.ok ? "pool" : "pool_short", { have: p.have, need: p.need }); },
        shortText: function () { var p = this.P(); return this.ui("short_text", { have: p.have, need: p.need }); },
        handCount: function () { return Object.keys(this.s.pick || {}).length + Object.keys(this.s.pin || {}).length; },
        handLine: function () { return this.ui("picked_n", { n: this.handCount() }); },
        resetHand: function () {
          var raw = clone(this.s);
          raw.pick = {};
          raw.pin = {};
          this.apply(raw);
        },
        /** "Choose squares yourself": the squares offered in the card's language on the event's day, by category, the
         *  search applied — [{ cat, name, rows: [{ id, item, text, pub, on, pin }] }] (GVBingo.pickRows: "always"
         *  ticked only on a square in use). Each kind is a folded list of its own (openCats), all open while a search
         *  is typed. */
        pickGroups: function () {
          var rev = this.rev, q = fold(this.q).trim();
          if (!G || !D) return [];
          var key = rev + "\u0001" + q;
          if (M.pickKey === key && M.pick) return M.pick;
          var s = this.s, cw = this.cw(), words = q ? q.split(/\s+/) : [];
          var by = {};
          G.pickRows(D.items, s).forEach(function (r) {
            var it = r.item;
            var text = G.fillEvent(it.text[s.lang], s.event, { thisEvent: cw.this_event });
            if (words.length) {
              var hay = fold(text + " " + (it.short && it.short[s.lang] || ""));
              for (var i = 0; i < words.length; i++) if (hay.indexOf(words[i]) < 0) return;
            }
            (by[it.cat] = by[it.cat] || []).push({ id: it.id, item: it, text: text, pub: it.pub, on: r.on, pin: r.pin });
          });
          var out = [];
          (D.cats || []).forEach(function (c) {
            if (by[c] && by[c].length) out.push({ cat: c, name: (D.catNames && D.catNames[c]) || c, rows: by[c] });
          });
          M.pickKey = key;
          M.pick = out;
          return out;
        },
        /** A search typed in "Choose squares yourself" (every kind of squares opens). */
        searching: function () { return fold(this.q).trim() !== ""; },
        /** A kind of squares opened by hand before (the list drawn again: it comes back open). */
        catOpen: function (c) { return !!this.openCats[c]; },
        /** A kind of squares opened or closed by hand (the page calls it only while no search is typed). */
        catToggled: function (c, open) {
          if (!!this.openCats[c] === !!open) return;
          var o = clone(this.openCats);
          if (open) o[c] = true; else delete o[c];
          this.openCats = o;
        },
        pick: function (item, on) { this.apply(G.setPick(this.s, item, on)); },
        pin: function (item, on) { this.apply(G.setPin(this.s, item, on)); },
        pickAll: function (g, on) {
          var n = this.s;
          g.rows.forEach(function (r) { n = G.setPick(n, r.item, on); });
          this.apply(n);
        },
        // the cards
        countInput: function (v) {
          if (/^\d{1,2}$/.test(String(v).trim())) {
            var n = +v;
            if (n >= 1 && n <= 60 && n !== this.s.count) this.set("count", n);
          }
        },
        countDone: function (input) { if (input) input.value = String(this.s.count); },
        codeDone: function () {
          var c = G.cleanCode(this.codeDraft);
          if (!c) { this.codeErr = true; return; }
          this.codeErr = false;
          this.codeDraft = c;
          if (c !== this.s.code) this.set("code", c);
        },
        shuffle: function () {
          this.codeErr = false;
          this.set("code", G.newCode());
          this.codeDraft = this.s.code;
        },
        perOf: function () { return G ? G.perSheetOf(this.s) : 1; },
        perOk: function (n) { return G ? G.perSheetChoices(this.s).indexOf(n) >= 0 : n === 1; },

        /* ================= the lines under the preview ================= */
        cardLine: function () { return this.ui("card_n", { n: this.idx + 1, total: this.s.count }); },
        previewLabel: function () { return this.ui("preview_of", { n: this.idx + 1, total: this.s.count }); },
        sheetLine: function () {
          if (!G) return "";
          var per = this.perOf(), sheets = Math.ceil(this.s.count / per);
          var paper = this.ui(this.s.paper === "a4" ? "paper_a4" : "paper_letter");
          if (this.s.count === 1) return this.ui("sheet_one", { paper: paper });
          return this.ui(sheets === 1 ? "sheet_many" : "sheets", { count: this.s.count, sheets: sheets, paper: paper });
        },
        busyText: function () {
          return this.done > 0 && this.done < this.s.count ? this.ui("preparing_n", { count: this.s.count, done: this.done })
            : this.ui("preparing", { count: this.s.count });
        },
        go: function (d) {
          this.idx = clamp(this.idx + d, 0, this.s.count - 1);
          this.draw();
        },

        /* ================= drawing ================= */
        /** The card's size and scale for these settings: { sheet, w, h (inches), k, side, sw, sh (the sheet) }. */
        dims: function () {
          var sh = G.sheetPlan(this.s);
          var sw = r3(sh.area.w), shh = r3(sh.area.h - SAFE_H);
          var w = r3((sw - sh.gap * (sh.across - 1)) / sh.across), h = r3((shh - sh.gap * (sh.down - 1)) / sh.down);
          var k = G.cardPlan(this.s, { w: w, h: h }).scale;
          return { sheet: sh, w: w, h: h, k: k, side: r3(SIDE_IN * k), sw: sw, sh: shh };
        },
        /** A small card (2 or 4 on a sheet): the short "How to play" (and its own floor for the strips' size). */
        compactNow: function () {
          if (!G || !this.s.rows) return false;
          var d = this.dims();
          return d.w < COMPACT_IN || d.h < COMPACT_IN;
        },
        /** The run's view for buildCard (its header says what is in it): with the strip's shortest lines and the head as
         *  typed — or as `lay` says (placeCard's: { layout, side, form, head, sub }). */
        view: function (dims, lay) {
          var s = this.s, cw = this.cw(), info = D.info || {};
          var title = String(s.title || "").replace(/\s+/g, " ").trim();
          var ev = String(s.event || "").replace(/\s+/g, " ").trim();
          var compact = dims.w < COMPACT_IN || dims.h < COMPACT_IN;
          var typed = String(s.rules || "").trim();
          var v = {
            s: s, cw: cw, info: info, dims: dims, layout: "stack", sidePx: 0, form: stripForms(info)[0] || "", head: null,
            compact: compact, typedHead: !!(title || ev), title: title || cw.title, ev: ev,
            date: longDate(s.date, s.lang), dateShort: shortDate(s.date, s.lang),
            rules: typed && !(compact && typed.length > RULES_COMPACT_MAX) ? s.rules : this.defaultRules(compact),
          };
          v.sub = subOf(v, "long");
          if (lay) {
            v.layout = lay.layout || "stack";
            v.sidePx = v.layout !== "stack" ? lay.side : 0;
            v.form = lay.form;
            v.head = lay.head;
            v.sub = lay.sub;
          }
          return v;
        },
        /** Every square the run may draw, each once (GVBingo.poolCells; one of each words, mark and label), with the
         *  short words or not — for THE FLOOR (placeCard). Kept until the settings change. */
        runCells: function (dense) {
          if (M.cellsRev !== this.rev) { M.cellsRev = this.rev; M.cells = {}; }
          var k = dense ? "dense" : "full";
          if (!M.cells[k]) {
            var seen = {}, out = [];
            G.poolCells(D.items, this.s, coreWords(this.cw()), { dense: !!dense }).forEach(function (c) {
              var key = c.mark + "\u0001" + c.text + "\u0001" + c.label;
              if (!seen[key]) { seen[key] = 1; out.push(c); }
            });
            M.cells[k] = out;
          }
          return M.cells[k];
        },
        queueDraw: function () {
          var self = this;
          if (T.draw) return;
          var run = function () { T.draw = 0; self.draw(); };
          T.draw = window.requestAnimationFrame ? window.requestAnimationFrame(run) : setTimeout(run, 16);
        },
        /** The preview: card idx, built, laid out and measured (LAYOUT: what the whole run takes), fitted and scaled to
         *  its column. */
        draw: function () {
          var stage = this.$refs.stage;
          if (!this.ready || !stage) return;
          var p = this.P();
          // (no card: nothing measured — no help line about its squares or its head)
          if (!p.ok) { stage.textContent = ""; stage.style.height = ""; this.cellIn = 0; this.headStep = 0; return; }
          // not laid out (the page printing, the preview hidden): nothing to measure — drawn when it shows again
          T.hidden = !stage.offsetWidth;
          if (T.hidden) return;
          try {
            var self = this, info = D.info || {};
            var words = coreWords(this.cw());
            var card = G.card(D.items, this.s, this.idx, words);
            if (!card || card.error) { stage.textContent = ""; return; }
            var dims = this.dims();
            var v = this.view(dims), a = buildCard(card, v);
            var paper = el("div", "bgo-paper");
            paper.appendChild(a);
            stage.textContent = "";
            stage.appendChild(paper);
            // (what the floor measured of each square, kept while the fonts, the card's language and the page's look
            // stay the same — FLOOR_KEEP squares at most —, and its counts for the run, kept until the settings change
            // too: LAYOUT)
            var look = T.fonts + ":" + this.s.lang + ":" + pageLook();
            if (!M.floor || M.floor.look !== look || M.floor.n > FLOOR_KEEP) {
              var probe = el("div", "bgo-grid bgo-probe");
              probe.setAttribute("aria-hidden", "true");
              M.floor = { look: look, n: 0, recs: {}, probe: probe };
              M.keepKey = "";
            }
            var key = this.rev + ":" + look;
            if (M.keepKey !== key) { M.keepKey = key; M.keep = {}; }
            var keep = M.keep, store = M.floor;
            var lay = placeCard(a, card, dims, v, function (c, dense, px, bar) {
              return floorMisses(c, self.runCells(dense), info, dense, px, keep, bar, store);
            });
            // the short words when the squares, as drawn, are small (denseAt)
            if (lay.dense !== card.dense) {
              card = G.card(D.items, this.s, this.idx, words, { dense: lay.dense });
              var b = buildCard(card, this.view(dims, lay));
              paper.replaceChild(b, a);
              a = b;
            }
            this.layout = lay.layout;
            this.sidePx = lay.side;
            this.form = lay.form;
            this.headStep = lay.step;
            this.sub = lay.sub;
            this.head = lay.head;
            this.dense = lay.dense;
            this.cellIn = lay.cellIn;
            fitCards([a]);
            this.scale();
          } catch (e) {
            if (window.console) console.error("[bingo]", e);
          }
        },
        /** The preview card scaled to the stage's width (never above its real size). Where the column sticks beside
         *  the settings (main.css sticky-aside: position sticky, a max-height, its bottom 1.5rem faded), no taller than
         *  the column leaves it: measured — what is above the card in the column (the heading, the buttons, the print
         *  help, the sheet line, the pager) stays in view and the card ends above the faded edge; never under K_LEAST
         *  (a short window: the column scrolls, the lines above the card stay). "Actual size" (zoom): 1, the stage
         *  scrolls sideways. */
        scale: function () {
          var stage = this.$refs.stage;
          var paper = stage && stage.firstElementChild;
          var a = paper && paper.firstElementChild;
          if (!a) return;
          var cw = a.offsetWidth, ch = a.offsetHeight, sw = stage.clientWidth;
          if (!cw || !ch || !sw) return;
          var k = Math.min(1, sw / cw);
          var aside = stage.closest ? stage.closest(".bgo-aside") : null;
          var cs = aside ? getComputedStyle(aside) : null;
          var room = cs && cs.position === "sticky" ? parseFloat(cs.maxHeight) : 0;
          if (room > 0) {
            var above = stage.getBoundingClientRect().top - aside.getBoundingClientRect().top + aside.scrollTop;
            k = Math.min(k, Math.max(K_LEAST, (room - above - (parseFloat(cs.paddingBottom) || 0)) / ch));
          }
          this.fitK = r3(k);
          if (this.zoom) k = 1;
          stage.classList.toggle("is-zoom", k === 1 && cw > sw);
          paper.style.transform = "scale(" + r3(k) + ")";
          paper.style.left = Math.max(0, Math.round((sw - cw * k) / 2)) + "px";
          // (and the room of the sideways scroll bar, when the stage has one)
          stage.style.height = Math.ceil(ch * k) + Math.max(0, stage.offsetHeight - stage.clientHeight) + "px";
        },
        /** "Actual size": offered while the card is drawn small (or while it is on); on and off. */
        zoomOffered: function () { return this.zoom || this.fitK < ZOOM_UNDER; },
        toggleZoom: function () {
          this.zoom = !this.zoom;
          this.scale();
        },

        /* ================= printing ================= */
        /** "Print or save as PDF": once the fonts are in (the cards are fitted with the letters they print with), the
         *  sheets CHUNK cards at a time, a frame between (the page answers; the busy line counts), then the print
         *  window. A change of the settings meanwhile starts the sheets again; the browser's own Print (prepare) takes
         *  over a run under way. */
        printNow: function () {
          var self = this;
          this.flushTyped();
          if (!this.P().ok || this.busy) return;
          this.save();                 // (what was printed is what comes back)
          this.busy = true;
          this.done = 0;
          var fail = function (e) {
            if (e && window.console) console.error("[bingo]", e);
            if (T.job) self.cleanup(true);
            T.job = null;
            self.busy = false;
          };
          var run = function () {
            var job = null;
            try { job = self.start(); } catch (e) { fail(e); return; }
            if (!job) { fail(); return; }
            var next = function () {
              if (T.job !== job) { self.busy = false; return; }     // the browser's own Print took over
              try {
                if (job.rev !== self.rev) { job = self.start(); if (!job) { fail(); return; } }
                if (self.step(job, CHUNK)) {
                  self.done = job.at;
                  setTimeout(next, 0);
                  return;
                }
                self.finish(job);
              } catch (e) { fail(e); return; }
              self.busy = false;
              setTimeout(function () { window.print(); }, 60);
            };
            setTimeout(next, 0);
          };
          // (a frame for "Getting N cards ready…" to show, then the fonts, then the work)
          setTimeout(function () {
            var f = null;
            try { f = document.fonts && document.fonts.ready; } catch (e) { f = null; }
            if (f && typeof f.then === "function") f.then(run, run); else run();
          }, 30);
        },
        /** Every card on its sheets in #bgo-print, fitted, the paper's @page and html[data-print="bingo"] — all at once
         *  (the browser's own Print: beforeprint cannot wait). */
        prepare: function () {
          var job = this.start();
          if (!job) return false;
          while (this.step(job, job.cards.length)) { /* (one step does them all) */ }
          this.finish(job);
          return true;
        },
        /** A print run: the preview drawn now (its LAYOUT is the run's — a change of this very moment may still be
         *  waiting for its frame), the cards drawn, #bgo-print emptied and laid out out of sight. Null: no cards. */
        start: function () {
          if (!this.ready || !this.P().ok) return null;
          var root = document.getElementById("bgo-print");
          if (!root) return null;
          this.draw();
          var cards = G.cards(D.items, this.s, coreWords(this.cw()), { dense: this.dense });
          if (!cards || cards.error || !cards.length) return null;
          var dims = this.dims();
          var v = this.view(dims, { layout: this.layout, side: this.sidePx, form: this.form, head: this.head, sub: this.sub });
          root.textContent = "";
          root.classList.add("is-measuring");
          T.job = { root: root, cards: cards, dims: dims, v: v, at: 0, rev: this.rev, els: [] };
          return T.job;
        },
        /** The next sheets of a run, about n cards (whole sheets), built and fitted → true while cards are left. */
        step: function (job, n) {
          var dims = job.dims, sh = dims.sheet, per = sh.perSheet, made = [];
          var end = Math.min(job.cards.length, job.at + Math.max(per, Math.ceil(n / per) * per));
          for (var i = job.at; i < end; i += per) {
            var sheet = el("section", "bgo-sheet");
            sheet.style.cssText = "--sw:" + dims.sw + "in;--sh:" + dims.sh + "in;--cw:" + dims.w + "in;--ch:" + dims.h + "in;--across:" +
              sh.across + ";--down:" + sh.down + ";--gap:" + sh.gap + "in;--m:" + sh.margin + "in";
            var k = Math.min(per, job.cards.length - i);
            for (var j = i; j < i + k; j++) {
              var a = buildCard(job.cards[j], job.v);
              sheet.appendChild(a);
              made.push(a);
            }
            cutLines(sheet, dims, k);
            job.root.appendChild(sheet);
          }
          fitCards(made);
          job.els = job.els.concat(made);
          job.at = end;
          return job.at < job.cards.length;
        },
        /** The run's end: a last look (a side column that sticks out over the small print on any card — a longer
         *  "Card 10 of 60" — makes the whole run "stack": never seen in the checks, but nothing may overlap), then
         *  the paper's @page (margin 0: each sheet has the margin as its padding) and html[data-print="bingo"]. */
        finish: function (job) {
          if (job.v.layout !== "stack" && job.els.some(function (a) { return !fitsCard(a); })) {
            job.v.layout = "stack";
            job.v.sidePx = 0;
            job.root.textContent = "";
            job.at = 0;
            job.els = [];
            while (this.step(job, job.cards.length)) { /* (all at once) */ }
          }
          job.root.classList.remove("is-measuring");
          // the paper: an @page of its own while printing (the stylesheets have none: they print every page of the site)
          var st = document.getElementById("bgo-page");
          if (!st) {
            st = document.createElement("style");
            st.id = "bgo-page";
            document.head.appendChild(st);
          }
          st.textContent = "@page { size: " + job.dims.sheet.size + "; margin: 0; }";
          document.documentElement.setAttribute("data-print", "bingo");
          T.printed = job.rev;
          T.job = null;
        },
        /** After the print (afterprint), or a run that failed (force): the page as it was. A run under way keeps its
         *  sheets (an afterprint of an earlier print). */
        cleanup: function (force) {
          var r = document.documentElement;
          if (!force && (T.job || r.getAttribute("data-print") !== "bingo")) return;
          r.removeAttribute("data-print");
          var st = document.getElementById("bgo-page");
          if (st) st.parentNode.removeChild(st);
          var root = document.getElementById("bgo-print");
          if (root) { root.textContent = ""; root.classList.remove("is-measuring"); }
        },

        /* ================= the link, starting over ================= */
        copyLink: function (btn) {
          this.flushTyped();
          this.save();                 // (what was shared is what comes back)
          var hash = G.encode(this.s);
          try { history.replaceState(null, "", location.pathname + location.search + hash); } catch (e) { /* file:// */ }
          var url = location.href.split("#")[0] + hash;
          if (window.GV && window.GV.copy) window.GV.copy(url, btn);
        },
        /** The starting settings, keeping this code (nothing to lose when only the code differs from them). */
        isFresh: function () {
          return G.encode(this.s) === G.encode(G.normalize({ code: this.s.code, date: todayCentral() }, base));
        },
        /** "Start over": asked first in the page ("Start over?", focus on "Keep my settings") unless nothing would be
         *  lost. */
        askStartOver: function () {
          var self = this;
          this.flushTyped();
          if (this.isFresh()) { this.startOver(); return; }
          this.asking = true;
          this.$nextTick(function () { if (self.$refs.overNo) self.$refs.overNo.focus(); });
        },
        keepSettings: function () {
          var self = this;
          this.asking = false;
          this.$nextTick(function () { if (self.$refs.overBtn) self.$refs.overBtn.focus(); });
        },
        /** The starting settings, a new code and today's date; the link out of the address; kept so (a reload gives
         *  this new start). */
        startOver: function () {
          var self = this, asked = this.asking;
          this.asking = false;
          if (this.linkInAddress()) {
            try { history.replaceState(null, "", location.pathname + location.search); } catch (e) { /* file:// */ }
          }
          this.custom = false;
          this.idx = 0;
          this.q = "";
          this.openCats = {};
          this.codeErr = false;
          this.s = G.normalize({ code: G.newCode(), date: todayCentral() }, base);
          this.codeDraft = this.s.code;
          this.changed(true);
          this.save();
          if (asked) this.$nextTick(function () { if (self.$refs.overBtn) self.$refs.overBtn.focus(); });
        },
      };
    });
  });
})();
