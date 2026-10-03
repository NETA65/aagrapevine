/* The workshop presentations' player — /orientation/ ("Workshop presentations"): a pop-up slide show for each deck
   of config/presentations/ (the JSON at /orientation/presentations/<id>.json, fetched only when a deck is opened or
   printed), with speaker notes, an overview, Customize (versions, slides, editing, your details, Prepare, a "my
   version" file), a presenter view in a second window, and printing in four ways. The logic (what is in the show,
   the clock, the text) is presentations-core.js (window.GVP); this file is the screen. Plain JavaScript, no
   dependencies (loaded with `defer` after app.js and presentations-core.js); the page works without it (its
   cards keep the PowerPoint copy).

   Hooks on the page (src/pages/orientation.njk; the macro src/_includes/macros/presentations.njk adds the dialog
   shell, the strings and the decks' list as #gvp-config):
     a[data-pres-open="<id>"] (+ data-pres-mode="present|customize|presenter|overview")   opens the player
     button[data-pres-print="<id>"][data-pres-print-mode="slides|notes|handout|script"]  prints without opening it
       (a [data-pres-print] button with no id, or with no mode, takes them from the fields named "deck" and "mode"
       of its form or [data-pres-print-form] — the page's "Print or save a copy" card)
     [data-pres-status="<id>"]   filled here: "Changed on this device: 3 slides hidden, 2 edited · Last shown: slide
                                 12 of 48" (empty when there is nothing to say)
     [data-pres-reset="<id>"|"all"]  hidden until there is something to reset; asks first, then offers Undo (10 s)
     the address ?present=<id>[&mode=…]#slide-N   opens on load (#slide-N while open: a reload resumes there)
   Keys while open: → ↓ Space PageDown next · ← ↑ Shift+Space PageUp back · Home End · digits + Enter go to a slide
   · N notes · O overview · C customize · P presenter view · F full screen · B (or .) black screen · Esc closes the
   menu, the overview or the drawer first, then the player. Swipe or tap the slide's sides on touch. A notice over
   the slide ("3 of your details are still blank") never holds these keys: the next one the player acts on (a
   clicker's Page Down too) puts it away, and so does a slide change from the other window.
   Accessibility: a modal dialog (the page behind is inert, focus stays inside and goes back to the opener), every
   control labelled in the page language, a polite live region ("Slide 3 of 48: <title>"), each slide a labelled
   region marked lang="en" (the content is English; a slide written in Spanish says lang="es", a {lang:es} span
   too), English titles inside the Spanish controls marked lang="en". The small slide pictures (overview, the
   presenter view's next slide) are inert: nothing in them takes the focus.
   Storage: localStorage "gv-presentations-v1" (the presenter's version, presentations-core.js) and
   "gv-presentations-view" (notes open, notes size) — every read and write in try/catch: without storage it still
   presents (the changes then last until the page is closed, and the player says so once). Nothing is ever sent
   anywhere.
   Presenter view: a second window on ?present=<id>&mode=presenter, kept in step through a BroadcastChannel (a
   storage event where there is none): either window moves both. A blocked pop-up → "Presenter mode in this window".
   Print: a print-only container (#gvp-print) and html.gvp-printing while printing — the page's own print (the
   GVR / RLV 101 handout, areas/orientation.css) is hidden then; areas/presentations.css has the @page rules. The
   print window can also save it as a document (never called a "PDF" on this site). */
(function () {
  "use strict";
  var G = window.GVP;
  if (!G || !document.querySelector) return;

  /* ================================================================== 1. setup */
  var CFG = (function () {
    var node = document.getElementById("gvp-config");
    try { return node ? JSON.parse(node.textContent || "{}") : {}; } catch (e) { return {}; }
  })();
  var LANG = CFG.lang === "es" ? "es" : (document.documentElement.lang || "en").slice(0, 2) === "es" ? "es" : "en";
  var STRINGS = CFG.t || {};
  // the site's base path ("/aagrapevine/"), and where the decks' JSON files are
  var SITE_BASE = CFG.site || (window.SITE && window.SITE.base) || "/";
  var JSON_BASE = CFG.json || SITE_BASE.replace(/\/?$/, "/") + "orientation/presentations/";
  var META = {};
  (CFG.decks || []).forEach(function (d) { if (d && d.id) META[d.id] = d; });
  var VIEW_KEY = "gv-presentations-view";
  var SYNC_KEY = "gv-presentations-sync";
  var FLOOR = 0.62;            // the smallest a slide's text may shrink to fit (then it scrolls)
  var PRINT_FLOOR = 0.4;       // on paper nothing scrolls: an overlong slide shrinks further rather than lose its end
  var LOGICAL_W = 1280, LOGICAL_H = 720;
  var OLD_COPY_DAYS = 14;      // a deck file older than this (a copy kept offline) gets a word about its dates

  /** A control's words in the page language (src/_i18n/presentations.json via the macro); {name} filled in. */
  function T(key, vars) {
    var s = STRINGS[key];
    if (typeof s !== "string") s = key;
    return G.fmt(s, vars || {});
  }
  /** The singular or plural form of a count ("1 slide hidden" / "3 slides hidden"). */
  function TN(key, n, vars) {
    var v = Object.assign({ n: n }, vars || {});
    return T(n === 1 ? key + "_one" : key, v);
  }
  /** A control's words (key) into `parent` with its {name}s filled in; the names listed in `marked` (a slide's
   *  title, the deck's name: the content) become spans marked with the content's language (`lang`, English by
   *  default) when the page's differs — a screen reader says "Diapositiva 9 · " in Spanish and the title in
   *  English. */
  function tInto(parent, key, vars, marked, lang) {
    var s = STRINGS[key];
    if (typeof s !== "string") s = key;
    var l = lang || "en";
    var re = /\{(\w+)\}/g, at = 0, m;
    while ((m = re.exec(s))) {
      if (m.index > at) parent.appendChild(document.createTextNode(s.slice(at, m.index)));
      var v = vars && vars[m[1]] !== undefined && vars[m[1]] !== null ? String(vars[m[1]]) : m[0];
      if (marked && marked.indexOf(m[1]) >= 0 && l !== LANG) parent.appendChild(el("span", "", v)).setAttribute("lang", l);
      else parent.appendChild(document.createTextNode(v));
      at = re.lastIndex;
    }
    if (at < s.length) parent.appendChild(document.createTextNode(s.slice(at)));
    return parent;
  }
  /** The player's controls by name, in the page language: what {ui:customize} … says in the (English) notes —
   *  the same keys as presentations-core.js EN.ui. */
  var UI = (function () {
    var keys = { customize: "pres.customize_btn", version: "pres.tab_version", slides: "pres.tab_slides", edit: "pres.tab_edit",
      add: "pres.tab_add", your_details: "pres.tab_details", prepare: "pres.tab_prepare", save_share: "pres.tab_save",
      notes: "pres.notes_btn", overview: "pres.overview_btn", presenter_view: "pres.presenter_btn", print: "pres.print_btn",
      full_screen: "pres.full", black_screen: "pres.black_btn" };
    var out = {};
    Object.keys(keys).forEach(function (k) { if (typeof STRINGS[keys[k]] === "string") out[k] = STRINGS[keys[k]]; });
    return out;
  })();
  function reducedMotion() {
    try { return window.GV && window.GV.reducedMotion ? window.GV.reducedMotion() : window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) { return false; }
  }

  /* ------------------------------------------------------------------ storage */
  var STATE = G.emptyState();
  var storageOk = true;
  var warnedNoStorage = false;   // "This browser isn't keeping your changes" is said once a visit
  function loadState() {
    try {
      STATE = G.normState(localStorage.getItem(G.STORAGE_KEY));
      storageOk = true;
    } catch (e) {
      storageOk = false;          // private window, blocked storage: keep what we have in memory
    }
    return STATE;
  }
  /** Writes a state to storage (throws when storage is blocked). A deck with nothing of the presenter's (just
   *  opened, or reset) is not written down — only in the copy that is stored: the objects in STATE stay
   *  (Customize holds them). */
  function writeState(state) {
    var out = { v: state.v, shared: state.shared, decks: {} };
    Object.keys(state.decks).forEach(function (id) {
      var d = state.decks[id];
      if (G.summary(d).any || d.last) out.decks[id] = d;
    });
    var empty = !Object.keys(out.decks).length && !Object.keys(state.shared.fill).length;
    if (empty) localStorage.removeItem(G.STORAGE_KEY);
    else localStorage.setItem(G.STORAGE_KEY, JSON.stringify(out));
  }
  function saveState() {
    try {
      writeState(STATE);
      storageOk = true;
    } catch (e) {
      storageOk = false;
    }
    // the first change that cannot be kept says so — also when storage was already blocked as the player opened
    // (a private window, site data turned off), which is when it matters most
    if (!storageOk && P.root && !warnedNoStorage) { warnedNoStorage = true; toast(T("pres.no_storage")); }
    noStorageLine();
    renderStatuses();
  }
  /** The line in Customize while this browser keeps nothing. */
  function noStorageLine() {
    var line = q("[data-gvp-nostore]");
    if (line) line.hidden = storageOk;
  }
  function touch(ds) { if (ds) ds.updated = new Date().toISOString(); }
  var VIEW = { notes: false, size: 1 };
  function loadView() {
    try {
      var v = JSON.parse(localStorage.getItem(VIEW_KEY) || "null");
      if (v && typeof v === "object") {
        VIEW.notes = v.notes === true;
        if (typeof v.size === "number" && v.size >= 0.8 && v.size <= 2) VIEW.size = v.size;
      }
    } catch (e) { /* defaults */ }
  }
  function saveView() {
    try { localStorage.setItem(VIEW_KEY, JSON.stringify(VIEW)); } catch (e) { /* not kept */ }
  }

  /* ------------------------------------------------------------------ the decks (fetched on demand) */
  var DECKS = {};
  var PENDING = {};
  /** The deck's JSON (no-cache: the service worker answers network first, its copy when offline). */
  function fetchDeck(id) {
    if (DECKS[id]) return Promise.resolve(DECKS[id]);
    if (PENDING[id]) return PENDING[id];
    var url = (META[id] && META[id].json) || JSON_BASE + encodeURIComponent(id) + ".json";
    PENDING[id] = fetch(url, { cache: "no-cache", credentials: "same-origin" }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function (d) {
      if (!d || d.app !== "gv-presentation" || d.id !== id || !Array.isArray(d.slides)) throw new Error("not a deck");
      DECKS[id] = d;
      delete PENDING[id];
      return d;
    }, function (e) {
      delete PENDING[id];
      throw e;
    });
    return PENDING[id];
  }
  /** The presenter's version of a deck, made consistent with the deck as it is now (an updated deck). opts.save
   *  false: only fit it — a change another window stored, read back here, is never written again from here (two
   *  windows holding two deck files would otherwise keep rewriting it for each other). */
  function prepare(deck, opts) {
    var ds = G.deckState(STATE, deck.id);
    var before = ds.seen;
    var rec = G.reconcile(deck, ds);
    if (rec.changed && before && !(opts && opts.save === false)) saveState();
    if (rec.newer) refetchNewer(deck.id, ds.seen_built);
    return rec;
  }
  /** Another window has a newer file of this deck (the committee changed it in between, or this window got the
   *  service worker's older copy): fetch it once, network first, and show that — never prune the state down to the
   *  older file's slides. Without a connection the older file stays. */
  var REFETCHED = {};
  function refetchNewer(id, built) {
    var key = id + "@" + built;
    if (REFETCHED[key]) return;
    REFETCHED[key] = true;
    delete DECKS[id];
    fetchDeck(id).then(function (fresh) {
      if (!P.root || !P.deck || P.deck.id !== id || fresh === P.deck) return;
      if (Date.parse(fresh.built || "") <= Date.parse(P.deck.built || "")) return;
      P.deck = fresh;
      prepare(fresh, { save: false });
      refresh();
      renderStage(0);
      renderChrome();
      renderNotesPanel();
      if (P.mode === "presenter") renderPresenter();
      if (P.drawer) renderPanel(P.tab);
    }, function () { /* offline: the file in hand stays */ });
  }

  /* ------------------------------------------------------------------ DOM helpers */
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
  function btn(cls, label, opts) {
    var b = el("button", cls);
    b.type = "button";
    opts = opts || {};
    if (opts.icon) b.appendChild(icon(opts.icon));
    if (label !== undefined && label !== null) {
      var s = el("span", opts.hideLabel ? "sr-only" : "gvp-btn-label", label);
      b.appendChild(s);
    }
    if (opts.aria) b.setAttribute("aria-label", opts.aria);
    if (opts.title) b.title = opts.title;
    return b;
  }
  /** An icon from the macro's #gvp-icons (lucide, as the site's {% icon %} draws them). */
  function icon(name) {
    var tpl = document.getElementById("gvp-icons");
    var src = tpl && tpl.content ? tpl.content.querySelector('[data-gvp-icon="' + name + '"]') : null;
    if (src) {
      var svg = src.cloneNode(true);
      svg.removeAttribute("data-gvp-icon");
      return svg;
    }
    return el("span", "gvp-icon-missing");
  }
  function clear(node) { while (node && node.firstChild) node.removeChild(node.firstChild); return node; }
  var uid = 0;
  function newId(prefix) { uid += 1; return (prefix || "gvp") + "-" + uid; }

  /* ------------------------------------------------------------------ text → elements */
  /** The core's nodes into `parent`, as text and plain elements only (never HTML). */
  function addNodes(parent, nodes) {
    (nodes || []).forEach(function (n) {
      if (n.t === "text") parent.appendChild(document.createTextNode(n.v));
      else if (n.t === "br") parent.appendChild(document.createElement("br"));
      else if (n.t === "blank") {
        var s = el("span", "gvp-blank", "[" + n.v + "]");
        parent.appendChild(s);
      } else if (n.t === "b") addNodes(parent.appendChild(el("strong")), n.c);
      else if (n.t === "i") addNodes(parent.appendChild(el("em")), n.c);
      else if (n.t === "lang") {
        var sp = el("span");
        sp.setAttribute("lang", n.lang);
        addNodes(parent.appendChild(sp), n.c);
      } else if (n.t === "a") {
        var a = el("a");
        a.href = n.href;
        if (/^https?:/i.test(n.href)) { a.target = "_blank"; a.rel = "noopener noreferrer"; }
        addNodes(a, n.c);
        parent.appendChild(a);
      }
    });
    return parent;
  }
  function ctxFor(cur, where) {
    return { deck: cur.deck, state: STATE, live: cur.live, cur: cur, where: where || "slide", base: SITE_BASE, lang: LANG, ui: UI };
  }
  /** `text` (tokens, **bold** …) into `parent`; a text that is wholly one {lang:es} span marks `parent` itself. */
  function richInto(parent, text, ctx) {
    var nodes = G.rich(text, ctx);
    if (nodes.length === 1 && nodes[0].t === "lang" && parent.childNodes.length === 0) {
      parent.setAttribute("lang", nodes[0].lang);
      nodes = nodes[0].c;
    }
    return addNodes(parent, nodes);
  }
  function plainText(text, ctx) { return G.plain(G.rich(text, ctx)); }

  /* ================================================================== 2. a slide
     One renderer for every place a slide is drawn: the stage, the thumbnails (overview, presenter view), the
     printed pages. A slide is a 1280 × 720 "logical px" canvas laid out like the PowerPoint decks (decks/kit.py:
     13.333 × 7.5 in = 1280 × 720 px at 96 px/in, margins 72, eyebrow 21, title 48, body 32 …), scaled to fit
     its box (areas/presentations.css); on a phone held upright the same slide reflows instead. The variant
     "page" is a participants' handout page (Prepare → Print): the slide's content as a page of text. */
  var ACC = { gv: 1, lv: 1, vine: 1, grape: 1, navy: 1 };
  var EVENT_ACC = { gv: "gv", lv: "lv", booth: "vine", assembly: "grape", committee: "navy", other: "navy" };
  function accentOf(x) { return x && ACC[x] ? x : "gv"; }
  function num(n) { return typeof n === "number" ? String(Math.round(n * 100) / 100) : String(n || ""); }

  function renderSlide(e, cur, o) {
    o = o || {};
    var s = e.slide;
    var L = s.layout;
    var variant = o.variant || "stage";
    var tstyle = L === "text" && (s.style === "script" || s.style === "break") ? s.style : "";
    var root = el("section", "gvp-slide gvp-l-" + L + " gvp-a-" + accentOf(s.accent) + (variant === "page" ? " gvp-slide--page" : "")
      + (tstyle ? " gvp-t-" + tstyle : ""));
    root.setAttribute("lang", s.lang || cur.deck.lang || "en");
    root.setAttribute("data-slide", e.id);
    var ctx = ctxFor(cur, "slide");
    var R = function (tag, cls, text) { return richInto(el(tag, cls), text, ctx); };
    // the eyebrow's words in one inline box: the flex line keeps it at the bottom of its row, and a **bold** word,
    // a link or a [blank] in it stays part of one line of text
    var brow = function (text) { var p = el("p", "gvp-s-eyebrow"); p.appendChild(R("span", "", text)); return p; };
    var title = R("h2", "gvp-s-title", s.title || "");
    title.id = newId("gvp-st");
    if (variant === "stage") {
      root.setAttribute("aria-roledescription", T("pres.slide"));
      root.setAttribute("aria-labelledby", title.id);
    } else if (variant === "thumb") {
      // a picture of the slide (the overview, the presenter view's next slide): nothing in it takes the focus or is
      // read out — its button or label says which slide it is
      root.setAttribute("aria-hidden", "true");
      root.inert = true;
    } else root.setAttribute("aria-labelledby", title.id);      // printed: real headings, lists and paragraphs
    var fit = el("div", "gvp-s-fit");
    root.appendChild(fit);

    if (L === "title" || L === "closing") {
      root.appendChild(attrs(el("span", "gvp-s-deco"), { "aria-hidden": "true" }));
      var box = el("div", "gvp-s-hero");
      if (L === "title" && s.eyebrow) box.appendChild(brow(s.eyebrow));
      box.appendChild(title);
      if (L === "title") {
        if (s.subtitle) box.appendChild(R("p", "gvp-s-subtitle", s.subtitle));
        if (Array.isArray(s.lines) && s.lines.length) {
          var ls = el("div", "gvp-s-lines");
          s.lines.forEach(function (l) { ls.appendChild(R("p", "", l)); });
          box.appendChild(ls);
        }
      } else {
        if (s.message) box.appendChild(R("p", "gvp-s-subtitle", s.message));
        if (Array.isArray(s.lines) && s.lines.length) {
          var cl = el("div", "gvp-s-lines");
          s.lines.forEach(function (l) { cl.appendChild(R("p", "", l)); });
          box.appendChild(cl);
        }
      }
      fit.appendChild(box);
      if (L === "closing" && s.data && s.data.svg) {
        root.classList.add("has-qr");
        fit.appendChild(qrFigure(s.data, ""));
      }
      if (L === "title" && cur.deck.as_of) root.appendChild(el("p", "gvp-s-asof", G.fmt(G.EN.current_as_of, { date: cur.deck.as_of })));
      return root;
    }
    if (L === "section") {
      var sec = el("div", "gvp-s-sectionbox");
      // the part's number in its circle (a section the presenter added has none until they type one: no circle)
      if (num(s.number).trim()) {
        var badge = el("p", "gvp-s-num");
        badge.appendChild(el("span", "sr-only", "Part "));
        badge.appendChild(document.createTextNode(num(s.number)));
        sec.appendChild(badge);
      }
      var words = el("div", "gvp-s-secwords");
      words.appendChild(title);
      if (s.subtitle) words.appendChild(R("p", "gvp-s-subtitle", s.subtitle));
      sec.appendChild(words);
      fit.appendChild(sec);
      return root;
    }

    // a content slide: eyebrow + title, the layout's body, the takeaway and the sources line, the footer
    var head = el("header", "gvp-s-head");
    // a pause slide (style "break") goes without its part's eyebrow, as the decks draw it; one of its own stays
    var partBrow = s.part ? "Part " + s.part.n + " · " + s.part.title : "";
    if (s.eyebrow && !(tstyle === "break" && (s.eyebrow === partBrow || s.eyebrow === cur.deck.eyebrow))) head.appendChild(brow(s.eyebrow));
    head.appendChild(title);
    fit.appendChild(head);
    var body = el("div", "gvp-s-body");
    fit.appendChild(body);
    switch (L) {
      case "bullets": body.appendChild(list(s.items, ctx, { numbered: s.numbered, checklist: s.checklist })); break;
      case "columns": body.appendChild(columns(s, ctx)); break;
      case "table": body.appendChild(table(s.header, s.rows, s.widths, s.first_col_bold, ctx)); break;
      case "agenda": body.appendChild(agenda(e, cur, ctx)); break;
      case "quote": body.appendChild(quote(s, ctx)); break;
      case "activity": body.appendChild(activity(s, ctx)); break;
      case "qa":
        if (Array.isArray(s.prompts) && s.prompts.length) body.appendChild(list(s.prompts, ctx, {}));
        if (s.note) body.appendChild(R("p", "gvp-s-note", s.note));
        break;
      case "resources": body.appendChild(resources(s, cur, ctx)); break;
      case "credits": credits(body, s, ctx); break;
      case "text": body.appendChild(textBody(s.body, ctx, tstyle)); break;
      case "flow": body.appendChild(flow(s, ctx)); break;
      case "live":
        if (s.intro) body.appendChild(R("p", "gvp-s-intro", s.intro));
        body.appendChild(liveBlock(s, cur, ctx));
        break;
      default: break;
    }
    // a pause slide whose title is its message ("Break: 10 minutes", no large first line of its own): the title and
    // the words under it together, in the middle of the slide
    if (tstyle === "break" && !body.querySelector(".gvp-s-text--break > .gvp-s-lead")) root.classList.add("gvp-t-break--title");
    if (s.takeaway && L !== "activity") body.appendChild(variant === "page" ? writeLines(s.takeaway, ctx) : R("p", "gvp-s-takeaway", s.takeaway));
    if (s.source) body.appendChild(R("p", "gvp-s-source", s.source));
    if (variant !== "page") {
      var foot = el("footer", "gvp-s-foot");
      foot.appendChild(richInto(el("span", "gvp-s-foottext"), cur.deck.footer || "", ctx));
      foot.appendChild(el("span", "gvp-s-pg", o.n === null || o.n === undefined ? "" : String(o.n)));
      root.appendChild(foot);
    }
    return root;
  }

  /** A printed handout page's highlighted box: its paragraphs one under the other, and a line that ends with ":"
   *  ("My first line:", "My title:") a place to write — a rule after the words, and a full line under all but the
   *  last, as the deck's planner page has them. */
  function writeLines(text, ctx) {
    var box = el("div", "gvp-s-takeaway gvp-s-takeaway--page");
    var paras = String(text || "").replace(/\r\n?/g, "\n").split(/\n[ \t]*\n/).filter(function (x) { return x.trim(); });
    paras.forEach(function (para, i) {
      var p = richInto(el("p", "gvp-s-tkline"), para.trim(), ctx);
      if (/:\s*(?:\*\*|_)?\s*$/.test(para.trim())) {
        p.classList.add("is-write");
        p.appendChild(attrs(el("span", "gvp-s-tkrule"), { "aria-hidden": "true" }));
        box.appendChild(p);
        if (i < paras.length - 1) box.appendChild(attrs(el("span", "gvp-s-tkline is-rule"), { "aria-hidden": "true" }));
      } else box.appendChild(p);
    });
    return box;
  }
  function list(items, ctx, opts) {
    opts = opts || {};
    var ul = el(opts.numbered ? "ol" : "ul", "gvp-s-list" + (opts.checklist ? " gvp-s-checklist" : "") + (opts.numbered ? " is-numbered" : ""));
    (Array.isArray(items) ? items : typeof items === "string" ? [items] : []).forEach(function (it) {
      var li = el("li");
      if (it && typeof it === "object") {
        li.appendChild(richInto(el("span", "gvp-s-li"), it.text || "", ctx));
        if (Array.isArray(it.items) && it.items.length) {
          var sub = el("ul", "gvp-s-sub");
          it.items.forEach(function (x) { sub.appendChild(richInto(el("li"), x, ctx)); });
          li.appendChild(sub);
        }
      } else richInto(li, it, ctx);
      ul.appendChild(li);
    });
    return ul;
  }
  /** Paragraphs separated by an empty line; a line starting with "- " is a list item. A paragraph that is all
   *  **bold** is a lead (gvp-s-lead). style "script": a read-aloud announcement — a card tinted in the slide's
   *  colour, its lead the instruction above the words, the words in the serif, each ‹blank› in the fill-in orange;
   *  "break": the pause slide's message, centred (its lead large). */
  function textBody(text, ctx, style) {
    var wrap = el("div", "gvp-s-text" + (style ? " gvp-s-text--" + style : ""));
    String(text || "").replace(/\r\n?/g, "\n").split(/\n[ \t]*\n/).forEach(function (para) {
      var ul = null, buf = [];
      var flush = function () {
        if (!buf.length) return;
        var p = richInto(el("p"), buf.join("\n"), ctx);
        if (isLead(p)) p.className = "gvp-s-lead";
        wrap.appendChild(p);
        buf = [];
      };
      para.split("\n").forEach(function (line) {
        var m = /^\s*[-•]\s+(.*)$/.exec(line);
        if (m) {
          flush();
          if (!ul) { ul = el("ul", "gvp-s-list"); wrap.appendChild(ul); }
          ul.appendChild(richInto(el("li"), m[1], ctx));
        } else if (line.trim()) { ul = null; buf.push(line); }
      });
      flush();
    });
    if (style === "script") markBlanks(wrap);
    return wrap;
  }
  /** A paragraph that is one **bold** run and nothing else. */
  function isLead(p) {
    var kids = Array.prototype.filter.call(p.childNodes, function (n) { return n.nodeType !== 3 || n.nodeValue.trim(); });
    return kids.length === 1 && kids[0].nodeName === "STRONG";
  }
  /** The script card's ‹blanks› (left for the practice, not the presenter's fill-ins), drawn in the fill-in orange. */
  function markBlanks(root) {
    var walker = document.createTreeWalker(root, 4);
    var texts = [];
    while (walker.nextNode()) if (/‹[^›\n]{1,120}›/.test(walker.currentNode.nodeValue)) texts.push(walker.currentNode);
    texts.forEach(function (t) {
      var frag = document.createDocumentFragment();
      var s = t.nodeValue, at = 0, re = /‹[^›\n]{1,120}›/g, m;
      while ((m = re.exec(s))) {
        if (m.index > at) frag.appendChild(document.createTextNode(s.slice(at, m.index)));
        frag.appendChild(el("span", "gvp-s-mark", m[0]));
        at = re.lastIndex;
      }
      if (at < s.length) frag.appendChild(document.createTextNode(s.slice(at)));
      t.parentNode.replaceChild(frag, t);
    });
  }
  function columns(s, ctx) {
    var cols = Array.isArray(s.columns) ? s.columns : [];
    var style = s.style === "cards" || s.style === "plain" ? s.style : "panels";
    var wrap = el("div", "gvp-s-cols gvp-s-cols--" + style + " gvp-s-cols-" + Math.max(1, Math.min(4, cols.length)));
    cols.forEach(function (c) {
      var col = el("div", "gvp-s-col gvp-a-" + accentOf(c.accent || s.accent));
      var head = String(c.heading || "");
      // "1 · One moment" on a card: the number big beside the heading (above it on three cards in a row), as the
      // decks draw numbered cards
      var m = style === "cards" ? /^(\d{1,2}|[A-Z])\s+·\s+(.+)$/.exec(head) : null;
      if (m) { col.classList.add("has-num"); col.appendChild(el("p", "gvp-s-colnum", m[1])); head = m[2]; }
      if (head) col.appendChild(richInto(el("h3", "gvp-s-colh"), head, ctx));
      if (c.gloss) col.appendChild(richInto(el("p", "gvp-s-gloss"), c.gloss, ctx));
      // `checklist: true` on the slide: tick boxes in place of bullets (a printed checklist to tick by hand)
      if (Array.isArray(c.items)) col.appendChild(list(c.items, ctx, { checklist: s.checklist === true }));
      else if (c.text) col.appendChild(textBody(c.text, ctx));
      wrap.appendChild(col);
    });
    return wrap;
  }
  /** The colour of a table's header cell: the magazine it names, else navy (decks/kit.py header_accents). */
  function headTone(h) {
    var x = String(h || "").trim();
    return /^grapevine\b/i.test(x) ? "gv" : /^la vi[ñn]a\b/i.test(x) ? "lv" : "navy";
  }
  function table(header, rows, widths, firstBold, ctx, tone) {
    var wrap = el("div", "gvp-s-tablewrap");
    var t = el("table", "gvp-s-table");
    var head = Array.isArray(header) && header.some(function (h) { return String(h).trim(); }) ? header : null;
    var n = head ? head.length : rows && rows[0] ? rows[0].length : 0;
    if (Array.isArray(widths) && widths.length === n) {
      var sum = widths.reduce(function (a, b) { return a + (Number(b) || 0); }, 0) || 1;
      var cg = el("colgroup");
      widths.forEach(function (w) { var c = el("col"); c.style.width = ((100 * (Number(w) || 0)) / sum).toFixed(2) + "%"; cg.appendChild(c); });
      t.appendChild(cg);
    }
    if (head) {
      var thead = el("thead"), tr = el("tr");
      head.forEach(function (h) {
        var th = el("th", "gvp-th-" + (tone || headTone(h)));
        th.scope = "col";
        richInto(th, String(h), ctx);
        tr.appendChild(th);
      });
      thead.appendChild(tr);
      t.appendChild(thead);
    }
    var tb = el("tbody");
    (rows || []).forEach(function (r) {
      var tr2 = el("tr");
      (Array.isArray(r) ? r : [r]).forEach(function (c, i) {
        var cell;
        if (c && typeof c === "object" && c.node) { cell = el("td"); cell.appendChild(c.node); }
        else {
          cell = el(i === 0 && firstBold ? "th" : "td");
          if (cell.tagName === "TH") cell.scope = "row";
          richInto(cell, String(c === null || c === undefined ? "" : c), ctx);
        }
        tr2.appendChild(cell);
      });
      tb.appendChild(tr2);
    });
    t.appendChild(tb);
    wrap.appendChild(t);
    return wrap;
  }
  function agenda(e, cur, ctx) {
    var rows = G.agendaRows(e, cur);
    var ol = el("ol", "gvp-s-agenda");
    var longest = 0;
    rows.forEach(function (r) { longest = Math.max(longest, String(r.time).length); });
    // the time column as wide as its longest time ("0:08", "1944", "Feb.–Mar.")
    ol.style.setProperty("--tw", Math.max(2.6, longest * 0.62 + 0.6).toFixed(2) + "em");
    if (rows.length > 9) {
      ol.classList.add("is-two");
      ol.style.setProperty("--rows", String(Math.ceil(rows.length / 2)));
    }
    rows.forEach(function (r) {
      var li = el("li");
      li.appendChild(richInto(el("span", "gvp-s-time"), r.time, ctx));
      var t = el("span", "gvp-s-agt");
      t.appendChild(richInto(el("strong"), r.title, ctx));
      if (r.detail) t.appendChild(richInto(el("span", "gvp-s-agd"), r.detail, ctx));
      li.appendChild(t);
      ol.appendChild(li);
    });
    return ol;
  }
  function quote(s, ctx) {
    var words = String(s.quote || "").split(/\s+/).filter(Boolean).length;
    var fig = el("figure", "gvp-s-quote" + (words > 70 ? " is-long" : ""));
    if (words <= 70) fig.appendChild(attrs(el("span", "gvp-s-qmark", "“"), { "aria-hidden": "true" }));
    var bq = el("blockquote");
    bq.appendChild(richInto(el("p"), s.quote || "", ctx));
    fig.appendChild(bq);
    // the credit line exactly as written (never a dash added)
    if (s.credit) fig.appendChild(richInto(el("figcaption"), s.credit, ctx));
    return fig;
  }
  function activity(s, ctx) {
    var wrap = el("div", "gvp-s-activity");
    var main = el("div", "gvp-s-actmain");
    main.appendChild(list(s.steps, ctx, { numbered: s.numbered !== false }));
    if (s.takeaway) main.appendChild(richInto(el("p", "gvp-s-takeaway"), s.takeaway, ctx));
    wrap.appendChild(main);
    var card = el("div", "gvp-s-timecard");
    card.appendChild(el("p", "gvp-s-tc-n", num(s.duration)));
    card.appendChild(el("p", "gvp-s-tc-u", Number(s.duration) === 1 ? G.EN.minute : G.EN.minutes));
    var mats = Array.isArray(s.materials) ? s.materials : s.materials ? [s.materials] : [];
    if (mats.length) {
      card.appendChild(el("p", "gvp-s-tc-h", G.EN.you_need));
      card.appendChild(list(mats, ctx, {}));
    }
    wrap.appendChild(card);
    return wrap;
  }
  function resources(s, cur, ctx) {
    var links = Array.isArray(s.links) ? s.links : [];
    var ul = el("ul", "gvp-s-links" + (links.length > 3 ? " is-two" : ""));
    links.forEach(function (k) {
      var li = el("li", "gvp-s-linkcard");
      li.appendChild(richInto(el("strong", "gvp-s-lklabel"), k.label || "", ctx));
      var href = G.safeHref(k.url, { base: SITE_BASE, lang: LANG });
      var shown = G.showUrl(k.url, cur.deck.site && cur.deck.site.host);
      if (href) {
        var a = el("a", "gvp-s-lkurl", shown);
        a.href = href;
        if (/^https?:/i.test(href)) { a.target = "_blank"; a.rel = "noopener noreferrer"; }
        li.appendChild(a);
      } else if (k.url) li.appendChild(el("span", "gvp-s-lkurl", k.url));
      if (k.note) li.appendChild(richInto(el("span", "gvp-s-lknote"), k.note, ctx));
      ul.appendChild(li);
    });
    return ul;
  }
  function credits(body, s, ctx) {
    body.appendChild(list(s.sources, ctx, {}));
    if (s.note) body.appendChild(richInto(el("p", "gvp-s-note"), s.note, ctx));
    // the standard lines, only when the slide does not already say it (decks/kit.py credits())
    var said = /not an official aa grapevine/i.test(JSON.stringify([s.sources, s.note]));
    if (s.disclaimer && !said) G.EN.disclaimer.forEach(function (l) { body.appendChild(el("p", "gvp-s-note", l)); });
  }
  function flow(s, ctx) {
    var steps = Array.isArray(s.steps) ? s.steps : [];
    var ol = el("ol", "gvp-s-flow gvp-s-flow-" + Math.max(2, Math.min(6, steps.length)));
    steps.forEach(function (st) {
      var li = el("li", "gvp-s-step");
      li.appendChild(richInto(el("strong"), (st && st.title) || "", ctx));
      if (st && st.text) li.appendChild(richInto(el("span"), st.text, ctx));
      ol.appendChild(li);
    });
    return ol;
  }
  function qrFigure(d, caption) {
    var fig = el("figure", "gvp-s-qr");
    var img = el("img");
    // the build's QR code (an SVG of squares) as a picture: an <img> never runs anything inside it
    img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(String(d.svg || ""));
    img.alt = "QR code: " + (d.label || d.url || "");
    img.width = 264;
    img.height = 264;
    fig.appendChild(img);
    fig.appendChild(el("figcaption", "", caption || d.label || ""));
    return fig;
  }

  /* ------------------------------------------------------------------ live blocks (the site's facts) */
  function seeLine(url, deck) {
    var p = el("p", "gvp-live-none");
    var shown = G.showUrl(url || "", deck && deck.site && deck.site.host);
    var parts = G.EN.none.split("{url}");
    p.appendChild(document.createTextNode(parts[0]));
    if (url) {
      var a = el("a", "", shown);
      a.href = url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      p.appendChild(a);
    }
    if (parts[1]) p.appendChild(document.createTextNode(parts[1]));
    return p;
  }
  function past(iso, now, slack) {
    var t = Date.parse(iso || "");
    return isFinite(t) && t + (slack || 0) < now;
  }
  /** After an English gloss that is a machine translation (a row's gloss_machine), as the site marks one. */
  function autoMark() { return el("small", "gvp-auto", " (" + G.EN.auto_translated + ")"); }
  function liveBlock(s, cur, ctx) {
    var d = s.data || {};
    var now = cur.nowMs;
    var box = el("div", "gvp-live gvp-live--" + String(s.kind || "x").replace(/[^a-z-]/g, ""));
    var EN = G.EN;
    var opts = s.options || {};
    // every row the build knows, less the past ones, within the slide's limits (presentations-core.js liveRows)
    var rowsNow = function () { return G.liveRows(s.kind, d, opts, now); };
    // where to look for a magazine's themes when the site lists none: "La Viña: see aalavina.org/recursos"
    var lookIn = function (pub, cls) {
      var where = pub === "lv" ? "aalavina.org/recursos" : "aagrapevine.org/contribute";
      return el("p", "gvp-live-none" + (cls ? " " + cls : ""), (pub === "lv" ? EN.lv : EN.gv) + ": " + G.fmt(EN.see, { where: where }));
    };
    switch (s.kind) {
      case "deadlines": {
        var rows = rowsNow();
        if (!rows.length) {
          // La Viña's own themes: its page (the site's /contribute/ has no La Viña dates when it lists none)
          if (opts.pub === "lv") box.appendChild(lookIn("lv"));
          else {
            box.appendChild(seeLine(d.url, cur.deck));
            if (opts.pub === "both") box.appendChild(lookIn("lv", "gvp-live-none--sub"));
          }
          break;
        }
        var pubs = [];
        rows.forEach(function (r) { if (pubs.indexOf(r.pub) < 0) pubs.push(r.pub); });
        var both = pubs.length > 1 || opts.pub === "both";
        var head = (both ? [EN.magazine] : []).concat([EN.issue, EN.theme, EN.due]);
        var body = rows.map(function (r) {
          var theme = el("span");
          var th = el("span", "", r.theme || "");
          if (r.theme_lang) th.setAttribute("lang", r.theme_lang);
          theme.appendChild(th);
          if (r.gloss) {
            theme.appendChild(document.createTextNode(" (" + r.gloss + ")"));
            if (r.gloss_machine === true) theme.appendChild(autoMark());
          }
          var cells = [r.issue || "", { node: theme }, r.due_label || ""];
          return (both ? [r.pub === "lv" ? EN.lv : EN.gv] : []).concat(cells);
        });
        // one magazine's table: its head in the magazine's colour, or the slide's navy when the slide says so
        var tone = both ? "navy" : s.accent === "navy" ? "navy" : pubs[0] === "lv" ? "lv" : "gv";
        box.appendChild(table(head, body, both ? [2, 2.4, 4, 2.4] : [2.4, 4.6, 2.6], both, ctx, tone));
        // both magazines asked for, one with nothing listed: where to look for it (never a table of one)
        if (opts.pub === "both" && pubs.length === 1) box.appendChild(lookIn(pubs[0] === "lv" ? "gv" : "lv", "gvp-live-none--sub"));
        break;
      }
      case "events": {
        var evs = rowsNow();
        if (!evs.length) { box.appendChild(seeLine(d.url, cur.deck)); break; }
        var ul = el("ul", "gvp-live-events" + (evs.length >= 4 ? " is-two" : ""));
        evs.forEach(function (r) {
          var li = el("li", "gvp-ev gvp-a-" + (EVENT_ACC[r.kind] || "navy"));
          li.appendChild(el("p", "gvp-ev-date", [r.date_label, r.all_day ? "" : r.time_label, r.tentative ? EN.tentative : ""].filter(Boolean).join(" · ")));
          var t = el("p", "gvp-ev-title");
          var href = /^https:\/\//i.test(r.url || "") ? r.url : "";
          if (href) {
            var a = el("a", "", r.title || "");
            a.href = href; a.target = "_blank"; a.rel = "noopener noreferrer";
            t.appendChild(a);
          } else t.textContent = r.title || "";
          li.appendChild(t);
          // a hybrid event (a place AND Zoom) shows both, as its card on the Events page does
          var place = [r.place, r.online ? (r.platform ? G.fmt(EN.online_on, { platform: r.platform }) : EN.online) : ""].filter(Boolean).join(" · ");
          if (place) li.appendChild(el("p", "gvp-ev-place", place));
          ul.appendChild(li);
        });
        box.appendChild(ul);
        break;
      }
      case "prices": {
        var ch = d.change || null;
        var at = ch ? Date.parse(ch.at || "") : NaN;
        var after = isFinite(at) && now >= at;
        var noticeFrom = ch ? Date.parse(ch.notice_from || "") : NaN;
        var noticeOn = ch && (!isFinite(noticeFrom) || now >= noticeFrom) && !past(ch.notice_until, now);
        var grid = el("div", "gvp-live-prices");
        ["gv", "lv"].forEach(function (pub) {
          var prs = (d.rows || []).filter(function (r) { return r.pub === pub; });
          if (!prs.length) return;
          var card = el("div", "gvp-price gvp-a-" + pub);
          card.appendChild(el("h3", "gvp-s-colh", pub === "lv" ? EN.lv : EN.gv));
          card.appendChild(el("p", "gvp-price-term", EN.one_year));
          var dl = el("dl");
          prs.forEach(function (r) {
            var row = el("div");
            row.appendChild(el("dt", "", r.plan === "digital" ? EN.digital : EN.print));
            var dd = el("dd", "", after && r.then ? r.then : r.price);
            if (!after && r.then && noticeOn && ch) dd.appendChild(el("span", "gvp-price-then", G.fmt(EN.from_date, { date: ch.label }) + ": " + r.then));
            row.appendChild(dd);
            dl.appendChild(row);
          });
          card.appendChild(dl);
          grid.appendChild(card);
        });
        if (!grid.children.length) { box.appendChild(seeLine(d.url, cur.deck)); break; }
        box.appendChild(grid);
        if (ch && noticeOn) {
          var note = el("p", "gvp-live-note", G.fmt(EN.new_prices, { date: ch.label }));
          if (ch.books_more) note.appendChild(document.createTextNode(" · " + G.fmt(EN.books_more, { amount: ch.books_more })));
          box.appendChild(note);
        }
        break;
      }
      case "meeting":
      case "lv-workshop": {
        // a date stays listed until the meeting is over (tonight's, while it runs)
        var dates = rowsNow();
        var facts = el("p", "gvp-live-facts");
        var bits = [];
        if (s.kind === "meeting" && d.rule) bits.push(d.rule);
        if (d.time) bits.push(d.time);
        facts.textContent = bits.join(" · ");
        if (bits.length) box.appendChild(facts);
        if (dates.length) {
          var many = dates.length > 4;
          var dl2 = el("ul", "gvp-live-dates" + (many ? " is-grid" : ""));
          dates.forEach(function (r, i) {
            var li = el("li", i === 0 ? "is-next" : "", r.label || "");
            dl2.appendChild(li);
          });
          box.appendChild(dl2);
        } else box.appendChild(seeLine(d.page || d.url, cur.deck));
        var z = [];
        if (d.zoom_id) z.push(EN.zoom_id + " " + d.zoom_id);
        if (d.passcode) z.push(EN.passcode + " " + d.passcode);
        if (s.kind === "lv-workshop" && d.contact) z.push(EN.contact + ": " + d.contact);
        if (z.length) box.appendChild(el("p", "gvp-live-zoom", z.join(" · ")));
        break;
      }
      case "issues": {
        var two = el("div", "gvp-s-cols gvp-s-cols--panels gvp-s-cols-2");
        [["gv", d.gv], ["lv", d.lv]].forEach(function (p) {
          if (!p[1]) return;
          var col = el("div", "gvp-s-col gvp-a-" + p[0]);
          col.appendChild(el("h3", "gvp-s-colh", (p[0] === "lv" ? EN.lv : EN.gv) + " · " + (p[1].label || "")));
          var th2 = el("p", "gvp-live-theme", p[1].theme || "");
          if (p[1].theme_lang) th2.setAttribute("lang", p[1].theme_lang);
          col.appendChild(th2);
          if (p[1].gloss) {
            var gl = col.appendChild(el("p", "gvp-s-gloss", p[1].gloss));
            if (p[1].gloss_machine === true) gl.appendChild(autoMark());
          }
          two.appendChild(col);
        });
        if (!two.children.length) box.appendChild(seeLine(d.url, cur.deck));
        else box.appendChild(two);
        break;
      }
      case "monthly": {
        var tips = rowsNow();
        if (!tips.length) { box.appendChild(seeLine(d.url, cur.deck)); break; }
        var cards = el("div", "gvp-s-cols gvp-s-cols--panels gvp-s-cols-" + Math.min(3, Math.max(1, tips.length)));
        tips.forEach(function (tip) {
          var col = el("div", "gvp-s-col gvp-a-vine");
          col.appendChild(el("h3", "gvp-s-colh", tip.title || ""));
          col.appendChild(el("p", "gvp-s-coltext", tip.text || ""));
          cards.appendChild(col);
        });
        box.appendChild(cards);
        break;
      }
      case "botm": {
        var books = [d].concat(d.also ? [d.also] : []).filter(function (b) { return b && b.title && !past(b.until, now); });
        if (!books.length) { box.appendChild(seeLine(d.url, cur.deck)); break; }
        var bk = el("div", "gvp-s-cols gvp-s-cols--panels gvp-s-cols-" + books.length);
        books.forEach(function (b) {
          // `mag` is the magazine's name as the Shop writes it ("Grapevine", "La Viña")
          var isLv = b.mag === "lv" || /vi[ñn]a/i.test(String(b.mag || ""));
          var col = el("div", "gvp-s-col gvp-a-" + (isLv ? "lv" : "gv"));
          col.appendChild(el("h3", "gvp-s-colh", isLv ? EN.lv : EN.gv));
          var bt = el("p", "gvp-live-theme", b.title);
          if (b.lang) bt.setAttribute("lang", b.lang);
          col.appendChild(bt);
          if (b.note) col.appendChild(el("p", "gvp-s-gloss", b.note));
          bk.appendChild(col);
        });
        box.appendChild(bk);
        break;
      }
      case "bulletin": {
        var posts = rowsNow();
        if (!posts.length) { box.appendChild(seeLine(d.url, cur.deck)); break; }
        var pl = el("ul", "gvp-live-posts");
        posts.forEach(function (r) {
          var li = el("li");
          if (r.date_label) li.appendChild(el("span", "gvp-ev-date", r.date_label));
          var a = el("a", "", r.title || "");
          if (/^https:\/\//i.test(r.url || "")) { a.href = r.url; a.target = "_blank"; a.rel = "noopener noreferrer"; }
          li.appendChild(a);
          pl.appendChild(li);
        });
        box.appendChild(pl);
        break;
      }
      case "qr": {
        if (!d.svg) { box.appendChild(seeLine(d.url, cur.deck)); break; }
        var fig = qrFigure(d, opts.caption || d.label);
        var u = el("p", "gvp-live-url", G.showUrl(d.url || "", ""));
        fig.appendChild(u);
        box.appendChild(fig);
        break;
      }
      default:
        if (d.url) box.appendChild(seeLine(d.url, cur.deck));
    }
    return box;
  }

  /* ------------------------------------------------------------------ fitting the text */
  function overflows(box) {
    return box.scrollHeight > box.clientHeight + 1 || box.scrollWidth > box.clientWidth + 1;
  }
  /** Shrinks a slide's type (its --fit, 1 → the floor, FLOOR on a screen) until its content fits the 1280 × 720
   *  canvas; past the floor the slide scrolls instead (is-scroll). Measured in the canvas' own (logical) pixels, so
   *  the result does not depend on the size it is shown at. Returns the factor. (The slides never move by a
   *  transition — areas/presentations.css — so what is read right after a change is the new size.) */
  function fitSlide(slide, floor) {
    var box = slide && slide.querySelector(".gvp-s-fit");
    if (!box) return 1;
    var min = typeof floor === "number" ? floor : FLOOR;
    slide.classList.remove("is-scroll");
    slide.style.setProperty("--fit", "1");
    if (!overflows(box)) return 1;
    slide.style.setProperty("--fit", String(min));
    if (overflows(box)) {
      slide.classList.add("is-scroll");
      return min;
    }
    var lo = min, hi = 1;
    for (var i = 0; i < 7; i++) {
      var mid = (lo + hi) / 2;
      slide.style.setProperty("--fit", mid.toFixed(4));
      if (overflows(box)) hi = mid; else lo = mid;
    }
    slide.style.setProperty("--fit", lo.toFixed(4));
    return lo;
  }

  /* ================================================================== 3. the player (a modal dialog) */
  var P = {
    root: null, deck: null, cur: null, i: 0, preview: null, mode: "present", drawer: "", tab: "slides",
    overview: false, black: false, opener: null, startUrl: "", inerted: [], reflow: false, menu: null,
    notice: null, digits: "", digitsTimer: 0, ro: null, ovro: null, lastSaveTimer: 0, fillNoticeShown: {},
    oldCopyShown: {},
  };
  function q(sel) { return P.root ? P.root.querySelector(sel) : null; }
  function qa(sel) { return P.root ? Array.prototype.slice.call(P.root.querySelectorAll(sel)) : []; }
  function currentEntry() {
    if (!P.cur) return null;
    return P.preview || P.cur.shown[P.i] || null;
  }
  function total() { return P.cur ? P.cur.shown.length : 0; }
  /** Everything the dialog shows, recomputed from the deck and the stored version (after any change). */
  function refresh() {
    if (!P.deck) return;
    var keep = currentEntry();
    var keepId = keep ? keep.id : "";
    P.cur = G.current(P.deck, STATE, "", Date.now());
    P.preview = null;
    var e = keepId ? P.cur.byId[keepId] : null;
    if (e && e.shown) P.i = e.n - 1;
    else if (e) {
      // the slide on the stage is not in the show (just turned off, or a preview): it stays there, marked, and
      // the arrows go on from its place
      P.preview = e;
      var at = P.cur.list.indexOf(e), j = 0;
      for (var k = 0; k < at; k++) if (P.cur.list[k].shown) j++;
      P.i = j;
    }
    P.i = Math.max(0, Math.min(total() - 1, P.i));
  }

  function openPlayer(id, opts) {
    opts = opts || {};
    var tpl = document.getElementById("gvp-tpl");
    if (!tpl || !tpl.content || !tpl.content.firstElementChild) return;
    if (P.root) {
      if (P.deck && P.deck.id === id) return;
      closePlayer(true);
    }
    loadState();
    loadView();
    P.opener = opts.opener || (document.activeElement !== document.body ? document.activeElement : null);
    if (!P.startUrl) {
      var sp = cleanSearch(location.search);
      P.startUrl = location.pathname + sp + (/^#slide-\d+$/.test(location.hash) ? "" : location.hash);
    }
    P.root = tpl.content.firstElementChild.cloneNode(true);
    P.mode = opts.mode === "presenter" ? "presenter" : "present";
    P.root.setAttribute("data-mode", P.mode);
    P.drawer = ""; P.overview = false; P.black = false; P.preview = null; P.deck = null; P.cur = null; P.i = 0;
    document.body.appendChild(P.root);
    P.inerted = Array.prototype.filter.call(document.body.children, function (n) {
      return n !== P.root && !/^(SCRIPT|TEMPLATE|STYLE|LINK)$/.test(n.tagName) && !n.hasAttribute("inert") && n.id !== "gvp-print";
    });
    P.inerted.forEach(function (n) { n.setAttribute("inert", ""); });
    document.documentElement.classList.add("gvp-open");
    applyTextScale();
    bindDialog();
    var stage = q("[data-gvp-stage]");
    clear(stage).appendChild(el("p", "gvp-loading", T("pres.loading")));
    noStorageLine();
    P.root.focus({ preventScroll: true });
    // this opening's own dialog: a file that arrives after the player was closed (or another one opened, even
    // the same deck again) is not this player's any more
    var root = P.root;
    fetchDeck(id).then(function (deck) {
      if (P.root !== root) return;
      start(deck, opts);
    }, function () {
      if (P.root !== root) return;
      var box = el("div", "gvp-loading");
      box.appendChild(el("p", "", T("pres.load_failed")));
      var retry = btn("gvp-pill", T("pres.retry"));
      retry.addEventListener("click", function () {
        var o = Object.assign({}, opts, { opener: P.opener });
        closePlayer(true);
        openPlayer(id, o);
      });
      box.appendChild(retry);
      var st = q("[data-gvp-stage]");
      if (st) clear(st).appendChild(box);
      retry.focus();
    });
  }

  function start(deck, opts) {
    P.deck = deck;
    var rec = prepare(deck);
    var short = deck.short || deck.title;
    // the deck's (English) name inside the page language's words: "<title> (presentación)", marked lang="en"
    var titleEl = q("[data-gvp-dialog-title]");
    if (titleEl) tInto(clear(titleEl), "pres.dialog_title", { title: deck.title }, ["title"]);
    qa("[data-gvp-short]").forEach(function (n) {
      n.textContent = short;
      if (LANG !== "en") n.setAttribute("lang", "en");
    });
    P.cur = G.current(deck, STATE, "", Date.now());
    var n = opts.slide || slideFromHash(location.hash) || 1;
    P.i = Math.max(0, Math.min(total() - 1, n - 1));
    observeStage();
    if (P.mode === "presenter") setMode("presenter");
    else if (VIEW.notes) setNotes(true, true);
    go(P.i, 0, { silent: P.mode !== "presenter", announce: true });
    fitBar();
    if (opts.mode === "customize") openDrawer(opts.tab || "slides");
    else if (opts.mode === "overview") openOverview();
    syncHello();
    // One notice at a time: the pop-up a browser blocked (the card's Presenter view), else the blanks before
    // presenting (once a visit; with a line about the slides the committee changed after the presenter edited
    // them), else those changed slides alone (each time, until the presenter chooses) — and none over Customize
    // (its Slides list marks the updated slides itself) or the overview, when the player opens into them.
    var blanks = P.mode === "present" && opts.mode !== "customize" && !P.fillNoticeShown[deck.id] ? G.emptyBlanks(P.cur, STATE) : [];
    var old = oldCopyText(deck);
    var busy = P.drawer || P.overview;              // opened into Customize or the overview: nothing over them
    if (opts.popupBlocked) popupNotice(old);
    else if (!busy && blanks.length) {
      P.fillNoticeShown[deck.id] = true;
      fillNotice(blanks, rec.stale.length, old);
    } else if (!busy && rec.stale.length) staleNotice(rec.stale.length, old);
    else if (old) toast(old);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { if (P.root) refit(); });
  }
  /** A deck file built weeks ago (a copy kept for offline use, opened without a connection) may show dates past
   *  their time: once a visit, a word with the file's date ("" otherwise). */
  function oldCopyText(deck) {
    var built = Date.parse(deck.built || "");
    if (!isFinite(built) || Date.now() - built < OLD_COPY_DAYS * 864e5 || P.oldCopyShown[deck.id]) return "";
    P.oldCopyShown[deck.id] = true;
    var day = "";
    try {
      day = new Date(built).toLocaleDateString(LANG === "es" ? "es-US" : "en-US", { month: "long", day: "numeric", year: "numeric", timeZone: "America/Chicago" });
    } catch (e) { day = new Date(built).toISOString().slice(0, 10); }
    return T("pres.old_copy", { date: day });
  }

  function closePlayer(quiet) {
    if (!P.root) return;
    try { if (fsEl()) (document.exitFullscreen || document.webkitExitFullscreen).call(document); } catch (e) { /* fine */ }
    unbindDialog();
    stopTimer(true);
    if (P.ro) { P.ro.disconnect(); P.ro = null; }
    if (P.ovro) { P.ovro.disconnect(); P.ovro = null; }
    flushLastSave();
    P.root.remove();
    P.root = null;
    P.inerted.forEach(function (n) { n.removeAttribute("inert"); });
    P.inerted = [];
    document.documentElement.classList.remove("gvp-open");
    try { history.replaceState(history.state, "", P.startUrl || location.pathname); } catch (e) { /* fine */ }
    P.startUrl = "";
    var deckId = P.deck ? P.deck.id : "";
    P.deck = null; P.cur = null; P.menu = null; P.notice = null; P.drawer = ""; P.overview = false; P.preview = null;
    renderStatuses();
    if (quiet) return;
    var back = P.opener && document.contains(P.opener) && P.opener.focus ? P.opener : document.querySelector('[data-pres-open="' + deckId + '"]:not(.gvp-st-resume)');
    P.opener = null;
    if (back && back.focus) back.focus({ preventScroll: true });
    // an opener that cannot take the focus now (a link of a card's "More" menu, closed since): its menu's button,
    // else the card's Present
    if (back && document.activeElement !== back) {
      var menu = back.closest && back.closest("details");
      var sum = menu && menu.querySelector("summary");
      if (sum) sum.focus({ preventScroll: true });
      if (document.activeElement !== sum) {
        var present = document.querySelector('a[data-pres-open="' + deckId + '"]:not([data-pres-mode]):not(.gvp-st-resume)');
        if (present) present.focus({ preventScroll: true });
      }
    }
  }
  // the address without ?present / &mode (what the page was before the player opened)
  function cleanSearch(search) {
    try {
      var p = new URLSearchParams(search);
      p.delete("present"); p.delete("mode");
      var s = p.toString();
      return s ? "?" + s : "";
    } catch (e) { return ""; }
  }
  function slideFromHash(hash) {
    var m = /^#slide-(\d+)$/.exec(hash || "");
    return m ? Number(m[1]) : 0;
  }
  function setUrl() {
    if (!P.root || !P.deck) return;
    try {
      var u = new URL(location.href);
      u.searchParams.set("present", P.deck.id);
      var mode = P.mode === "presenter" ? "presenter" : P.drawer ? "customize" : P.overview ? "overview" : "";
      if (mode) u.searchParams.set("mode", mode);
      else u.searchParams.delete("mode");
      var e = currentEntry();
      u.hash = e && e.shown ? "slide-" + e.n : "";
      history.replaceState(history.state, "", u.pathname + u.search + u.hash);
    } catch (err) { /* an old browser: the address just stays */ }
  }
  /** "Last shown: slide 12 of 48" on the page, after a pause (not a write per key press). */
  function rememberLast() {
    var e = currentEntry();
    if (!P.deck || !e || !e.shown) return;
    P.last = { n: e.n, of: total() };
    clearTimeout(P.lastSaveTimer);
    P.lastSaveTimer = setTimeout(writeLast, 800);
  }
  // Only the last slide is written here, into the stored copy as it is now: a change the other window (the
  // presenter view) just saved is never written over with this window's older copy — and the state in memory is
  // never swapped under the open panels (the storage event brings that window's changes here).
  function writeLast() {
    P.lastSaveTimer = 0;
    if (!P.deck || !P.last) return;
    var mem = G.deckState(STATE, P.deck.id);
    mem.last = P.last.n;
    mem.last_of = P.last.of;
    try {
      var stored = G.normState(localStorage.getItem(G.STORAGE_KEY));
      var d = G.deckState(stored, P.deck.id);
      d.last = P.last.n;
      d.last_of = P.last.of;
      writeState(stored);
    } catch (e) { /* no storage: it stays in memory */ }
    renderStatuses();
  }
  function flushLastSave() {
    if (P.lastSaveTimer) { clearTimeout(P.lastSaveTimer); writeLast(); }
  }

  /* ------------------------------------------------------------------ the stage */
  function applyTextScale() {
    var ts = 1;
    try { ts = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--text-scale")) || 1; } catch (e) { ts = 1; }
    if (P.root) P.root.style.setProperty("--ts", String(Math.max(1, Math.min(1.5, ts))));
  }
  function observeStage() {
    if (P.ro || !window.ResizeObserver) {
      if (!window.ResizeObserver) window.addEventListener("resize", onResize);
      return;
    }
    P.ro = new ResizeObserver(onResize);
    var w = q("[data-gvp-stagewrap]");
    if (w) P.ro.observe(w);
    var nx = q("[data-gvp-pvnext-stage]");
    if (nx) P.ro.observe(nx);
  }
  var resizeRaf = 0;
  function onResize() {
    if (resizeRaf) return;
    resizeRaf = requestAnimationFrame(function () {
      resizeRaf = 0;
      if (!P.root) return;
      fitBar();
      var before = P.reflow;
      layoutStage();
      if (before !== P.reflow) renderStage(0);
      layoutNext();
    });
  }
  /** The control bar always fits its row, whatever the window, the text size (Aa) or the language: first the
   *  buttons lose their words (the icon and its name stay), then Presenter view, Print and Full screen move into
   *  "More", and as a last resort the whole bar is drawn smaller (as the GVR / RLV 101 slides do on phones). */
  function fitBar() {
    var bar = q(".gvp-bar");
    if (!bar) return;
    bar.style.zoom = "";
    bar.classList.remove("is-compact", "is-tight");
    var over = function () { return bar.scrollWidth > bar.clientWidth + 1; };
    if (over()) bar.classList.add("is-compact");
    if (over()) bar.classList.add("is-tight");
    if (over()) bar.style.zoom = String(Math.max(0.6, bar.clientWidth / bar.scrollWidth).toFixed(3));
  }
  /** The stage's size: the 16:9 canvas scaled to fit (projector, laptop, tablet, a phone held sideways), or —
   *  in a narrow or very short space (a phone held upright, a browser zoomed far in) — the slide reflowed to the
   *  width, with type in rem (so the reading settings and zoom make it bigger) and its own scrolling. */
  function layoutStage() {
    var wrap = q("[data-gvp-stagewrap]"), stage = q("[data-gvp-stage]");
    if (!wrap || !stage) return;
    var W = wrap.clientWidth - 16, H = wrap.clientHeight - 16;
    var reflow = P.mode !== "presenter" && (W < 560 || H < 250);
    P.reflow = reflow;
    stage.classList.toggle("is-reflow", reflow);
    P.root.classList.toggle("is-reflow", reflow);
    if (reflow) {
      stage.style.width = ""; stage.style.height = "";
      return;
    }
    var k = Math.max(0.05, Math.min(W / LOGICAL_W, H / LOGICAL_H));
    stage.style.width = Math.floor(LOGICAL_W * k) + "px";
    stage.style.height = Math.floor(LOGICAL_H * k) + "px";
    stage.style.setProperty("--k", k.toFixed(5));
  }
  function renderStage(dir) {
    var stage = q("[data-gvp-stage]");
    if (!stage) return;
    var e = currentEntry();
    clear(stage);
    if (!e) {
      stage.appendChild(el("p", "gvp-loading", T("pres.no_slides")));
      return;
    }
    var canvas = el("div", "gvp-canvas");
    var sl = renderSlide(e, P.cur, { variant: "stage", n: e.shown ? e.n : null });
    canvas.appendChild(sl);
    stage.appendChild(canvas);
    layoutStage();
    if (!P.reflow) fitSlide(sl);
    if (dir && !reducedMotion()) {
      sl.classList.add(dir < 0 ? "is-in-back" : "is-in");
    }
    var tag = q("[data-gvp-preview]");
    if (tag) {
      tag.hidden = !P.preview;
      tag.textContent = P.preview ? previewText(P.preview) : "";
    }
    var blk = q("[data-gvp-black]");
    if (blk) blk.hidden = !P.black;
  }
  function refit() {
    var sl = q("[data-gvp-stage] .gvp-slide");
    if (sl && !P.reflow) fitSlide(sl);
    var nx = q("[data-gvp-pvnext-stage] .gvp-slide");
    if (nx) fitSlide(nx);
  }
  function previewText(e) {
    var why = e.why === "facilitator" ? T("pres.why_facilitator") : e.why === "window" ? T("pres.why_window") : T("pres.why_left_out");
    return T("pres.preview_tag", { why: why });
  }
  /** A slide taller than its box (reflowed, or past the fitting floor): the arrows scroll it before turning the
   *  page. true = scrolled. */
  function scrollSlide(dir, small) {
    var box = P.reflow ? q("[data-gvp-stage] .gvp-canvas") : q("[data-gvp-stage] .gvp-slide.is-scroll .gvp-s-fit");
    if (!box || box.scrollHeight <= box.clientHeight + 2) return false;
    var atEnd = dir > 0 ? box.scrollTop + box.clientHeight >= box.scrollHeight - 2 : box.scrollTop <= 1;
    if (atEnd) return false;
    var step = small ? Math.max(40, box.clientHeight * 0.15) : box.clientHeight * 0.85;
    try { box.scrollBy({ top: dir * step, behavior: reducedMotion() ? "auto" : "smooth" }); } catch (err) { box.scrollTop += dir * step; }
    return true;
  }

  /** Shows slide i (0-based in the show). opts.silent: do not move the other window (it moved us). */
  function go(i, dir, opts) {
    opts = opts || {};
    if (!P.cur) return;
    if (!total()) { renderStage(0); renderChrome(); return; }
    var was = currentEntry();
    i = Math.max(0, Math.min(total() - 1, i));
    P.preview = null;
    P.i = i;
    var e = currentEntry();
    var moved = !was || was.id !== e.id;
    // the presenter moved on (here, or in the other window): a notice is not left over the slide the room sees
    if (moved && was) hideNotice();
    renderStage(moved ? dir : 0);
    renderChrome();
    renderNotesPanel();
    if (P.mode === "presenter") renderPresenter();
    if (P.overview) markOverview();
    if (P.drawer) drawerFollow(moved);
    setUrl();
    rememberLast();
    if (moved || opts.announce) announce(e);
    if (!opts.silent) syncSend({ kind: "go", id: e.id });
  }
  function goToId(id, opts) {
    var e = P.cur && P.cur.byId[id];
    if (!e) return;
    if (e.shown) go(P.cur.shown.indexOf(e), 0, opts);
    else previewEntry(e);
  }
  /** A slide that is not in the show (left out, for the facilitator, outside its days) on the stage, marked. */
  function previewEntry(e) {
    P.preview = e;
    renderStage(0);
    renderChrome();
    renderNotesPanel();
    if (P.mode === "presenter") renderPresenter();
    if (P.drawer) drawerFollow(true);
    var live = q("[data-gvp-live]");
    if (live) live.textContent = previewText(e) + ": " + plainText(e.slide.title, ctxFor(P.cur, "slide"));
  }
  function announce(e) {
    var live = q("[data-gvp-live]");
    if (!live || !e) return;
    clear(live);
    live.appendChild(el("span", "", T("pres.live_slide", { n: e.n, total: total() }) + " "));
    var t = el("span", "", plainText(e.slide.title, ctxFor(P.cur, "slide")));
    t.setAttribute("lang", e.slide.lang || P.deck.lang || "en");
    live.appendChild(t);
  }
  function renderChrome() {
    var e = currentEntry();
    var n = e && e.shown ? e.n : 0;
    var count = q("[data-gvp-count]");
    if (count) count.textContent = (e && !e.shown ? "–" : String(n)) + " / " + total();
    var bar = q("[data-gvp-bar]");
    if (bar) bar.style.width = total() ? ((n / total()) * 100).toFixed(2) + "%" : "0";
    var prev = q('[data-gvp-act="prev"]'), next = q('[data-gvp-act="next"]');
    var hadFocus = document.activeElement;
    if (prev) prev.disabled = !P.preview && P.i <= 0;
    if (next) next.disabled = !P.preview && P.i >= total() - 1;
    if (hadFocus && hadFocus.disabled) P.root.focus({ preventScroll: true });
    pressed("notes", !q("[data-gvp-notes]").hidden);
    pressed("overview", P.overview);
    pressed("customize", !!P.drawer);
  }
  function pressed(act, on) {
    qa('.gvp-bar [data-gvp-act="' + act + '"]').forEach(function (b) { b.setAttribute("aria-pressed", on ? "true" : "false"); });
  }

  /* ------------------------------------------------------------------ notes */
  function setNotes(on, quiet) {
    var box = q("[data-gvp-notes]");
    if (!box) return;
    box.hidden = !on;
    if (P.mode !== "presenter" && !quiet) { VIEW.notes = on; saveView(); }
    renderNotesPanel();
    renderChrome();
    onResize();
  }
  function renderNotesPanel() {
    var box = q("[data-gvp-notes]");
    if (!box || box.hidden) return;
    var body = q("[data-gvp-notes-body]");
    renderNotes(body, currentEntry(), P.cur, { heading: q("[data-gvp-notes-title]") });
    box.style.setProperty("--notes-size", String(VIEW.size));
  }
  /** One slide's speaker notes into `target`: the version's own note (highlighted), the notes with their labels
   *  in bold and their links, and the TIME line for the current version. Shared with the printed notes. */
  function renderNotes(target, e, cur, o) {
    o = o || {};
    clear(target);
    if (!e) return target;
    var ctx = ctxFor(cur, "notes");
    if (o.heading) {
      o.heading.textContent = e.shown ? T("pres.notes_for", { n: e.n }) : T("pres.notes");
    }
    var pid = cur.preset ? cur.preset.id : "";
    var vn = e.slide.version_notes && pid && Object.prototype.hasOwnProperty.call(e.slide.version_notes, pid) && e.slide.version_notes[pid];
    if (vn) target.appendChild(richInto(el("p", "gvp-vnote"), vn, ctx));
    // the lines of this version only ({only:…} / {not:…} at a line's start)
    var lines = G.noteLines(e.slide.notes, pid);
    if (!lines.length) target.appendChild(el("p", "gvp-nonotes", T("pres.no_notes")));
    lines.forEach(function (l) {
      var p = el("p", "gvp-note");
      // a label names controls too ("YOU FILL IN ({ui:customize} → {ui:your_details}):"): its tokens are replaced
      // like the rest of the line's (the page's names, marked Spanish on /es/)
      if (l.label) { addNodes(p.appendChild(el("strong", "gvp-note-label")), G.rich(l.label, ctx)); p.appendChild(document.createTextNode(" ")); }
      richInto(p, l.text, ctx);
      target.appendChild(p);
    });
    var tl = G.timeLine(e);
    if (tl) {
      var m = /^(TIME:)\s*(.*)$/.exec(tl);
      var p2 = el("p", "gvp-note gvp-timeline");
      p2.appendChild(el("strong", "gvp-note-label", m ? m[1] : ""));
      p2.appendChild(document.createTextNode(" " + (m ? m[2] : tl)));
      target.appendChild(p2);
    }
    return target;
  }

  /* ------------------------------------------------------------------ overview */
  // what the overview covers (the stage, the notes, the top row, the presenter's bar): out of reach while it is open
  function coveredByOverview(on) {
    [".gvp-body", ".gvp-top", ".gvp-pvbar"].forEach(function (sel) { var n = q(sel); if (n) n.inert = on; });
  }
  function openOverview() {
    if (!P.cur) return;
    closeMenu();
    hideNotice();
    P.overview = true;
    var ov = q("[data-gvp-overview]");
    var grid = q("[data-gvp-ov-grid]");
    ov.hidden = false;
    coveredByOverview(true);
    clear(grid);
    P.cur.shown.forEach(function (e, i) {
      var li = el("li");
      var b = btn("gvp-thumb", null);
      // its name from its content ("Diapositiva 2: <span lang="en">Welcome</span>"): the title read in English
      tInto(b.appendChild(el("span", "sr-only")), "pres.thumb_label", { n: e.n, title: plainText(e.slide.title, ctxFor(P.cur, "slide")) }, ["title"], e.slide.lang);
      b.setAttribute("data-i", String(i));
      b.appendChild(attrs(el("span", "gvp-thumb-n", String(e.n)), { "aria-hidden": "true" }));   // (its name says it)
      var box = el("span", "gvp-thumb-box");
      var canvas = el("span", "gvp-canvas");
      canvas.appendChild(renderSlide(e, P.cur, { variant: "thumb", n: e.n }));
      box.appendChild(canvas);
      b.appendChild(box);
      li.appendChild(b);
      grid.appendChild(li);
    });
    sizeThumbs(grid);
    if (window.ResizeObserver && !P.ovro) {
      P.ovro = new ResizeObserver(function () { sizeThumbs(grid); });
      P.ovro.observe(grid);
    }
    fitLater(Array.prototype.slice.call(grid.querySelectorAll(".gvp-slide")));
    markOverview();
    renderChrome();
    setUrl();
    var curBtn = grid.querySelector('[aria-current="true"]') || grid.querySelector(".gvp-thumb");
    if (curBtn) { curBtn.focus({ preventScroll: true }); curBtn.scrollIntoView({ block: "nearest" }); }
  }
  function closeOverview(focusBack) {
    if (!P.overview) return;
    P.overview = false;
    var ov = q("[data-gvp-overview]");
    if (ov) ov.hidden = true;
    coveredByOverview(false);
    if (P.ovro) { P.ovro.disconnect(); P.ovro = null; }
    clear(q("[data-gvp-ov-grid]"));
    renderChrome();
    setUrl();
    if (focusBack !== false) {
      var b = q('.gvp-bar [data-gvp-act="overview"]');
      if (b && b.offsetParent) b.focus({ preventScroll: true }); else P.root.focus({ preventScroll: true });
    }
  }
  function markOverview() {
    qa("[data-gvp-ov-grid] .gvp-thumb").forEach(function (b) {
      var on = Number(b.getAttribute("data-i")) === P.i && !P.preview;
      if (on) b.setAttribute("aria-current", "true"); else b.removeAttribute("aria-current");
    });
  }
  /** Every thumbnail canvas scaled to its box (one width for all: a grid of equal columns). */
  function sizeThumbs(grid) {
    var box = grid && grid.querySelector(".gvp-thumb-box");
    if (!box) return;
    var k = box.clientWidth / LOGICAL_W;
    if (k > 0) grid.style.setProperty("--tk", k.toFixed(5));
  }
  /** Fits slides a few at a time (the overview's sixty thumbnails without a long pause). */
  function fitLater(slides) {
    var i = 0;
    function step() {
      var t0 = Date.now();
      while (i < slides.length && Date.now() - t0 < 12) fitSlide(slides[i++]);
      if (i < slides.length) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  /** The keys of the overview's grid: true when the key was the grid's own (arrows, Home, End, O). The player's
   *  other letters and digits go on to the usual shortcuts, the overview closing first where it would cover what
   *  they show (notes, Customize, the black screen, a slide number). */
  function overviewKey(e) {
    var k = e.key;
    if (/^[nNcCpPbB.0-9]$/.test(k)) {
      closeOverview(false);
      P.root.focus({ preventScroll: true });
      return false;
    }
    if (k === "f" || k === "F") return false;                    // full screen: the overview stays
    var items = qa("[data-gvp-ov-grid] .gvp-thumb");
    var at = items.indexOf(document.activeElement);
    if (at < 0) {                                                // (on the overview's own Close button)
      if (k === "o" || k === "O") { e.preventDefault(); closeOverview(); }
      return true;
    }
    var cols = 1;
    var top0 = items[0].getBoundingClientRect().top;
    while (cols < items.length && Math.abs(items[cols].getBoundingClientRect().top - top0) < 4) cols++;
    var to = at;
    if (k === "ArrowRight") to = at + 1;
    else if (k === "ArrowLeft") to = at - 1;
    else if (k === "ArrowDown") to = at + cols;
    else if (k === "ArrowUp") to = at - cols;
    else if (k === "Home") to = 0;
    else if (k === "End") to = items.length - 1;
    else if (k === "o" || k === "O") { e.preventDefault(); closeOverview(); return true; }
    else return true;
    e.preventDefault();
    to = Math.max(0, Math.min(items.length - 1, to));
    items[to].focus();
    items[to].scrollIntoView({ block: "nearest" });
    return true;
  }

  /* ------------------------------------------------------------------ menus (Print, More) */
  function toggleMenu(name, button) {
    if (P.menu && P.menu.name === name) { closeMenu(true); return; }
    closeMenu();
    var wrap = q('[data-gvp-menuwrap="' + name + '"]');
    if (!wrap) return;
    wrap.hidden = false;
    var r = button.getBoundingClientRect();
    var root = P.root.getBoundingClientRect();
    wrap.style.right = Math.max(8, root.right - r.right) + "px";
    wrap.style.bottom = Math.max(8, root.bottom - r.top + 6) + "px";
    button.setAttribute("aria-expanded", "true");
    P.menu = { name: name, button: button, wrap: wrap };
    var first = wrap.querySelector('[role="menuitem"]');
    if (first) first.focus();
  }
  function closeMenu(focusButton) {
    if (!P.menu) return;
    P.menu.wrap.hidden = true;
    P.menu.button.setAttribute("aria-expanded", "false");
    var b = P.menu.button;
    P.menu = null;
    if (focusButton && b.focus) b.focus({ preventScroll: true });
  }
  function menuKey(e) {
    var items = Array.prototype.slice.call(P.menu.wrap.querySelectorAll('[role="menuitem"]')).filter(function (x) { return !x.hidden; });
    var at = items.indexOf(document.activeElement);
    var k = e.key;
    if (k === "ArrowDown" || k === "ArrowUp") {
      e.preventDefault();
      var to = at < 0 ? 0 : (at + (k === "ArrowDown" ? 1 : -1) + items.length) % items.length;
      items[to].focus();
    } else if (k === "Home" || k === "End") {
      e.preventDefault();
      items[k === "Home" ? 0 : items.length - 1].focus();
    } else if (k === "Tab") closeMenu();
  }

  /* ------------------------------------------------------------------ notices, the toast */
  /** A short message over the stage with its buttons ([{ label, primary, run }]); `text`: a line, or several. It
   *  takes neither the focus nor the presenting keys (a clicker's next press puts it away, onKey): Tab reaches its
   *  buttons first, each described by its words, and a screen reader hears it once through its own live region. */
  function notice(title, text, buttons, onDismiss) {
    var box = q("[data-gvp-notice]");
    if (!box) return;
    clear(box);
    var h = el("p", "gvp-notice-h", title);
    h.id = newId("gvp-nh");
    box.appendChild(h);
    var lines = (Array.isArray(text) ? text : [text]).filter(Boolean);
    var ids = lines.map(function (t) {
      var p = el("p", "gvp-notice-text", t);
      p.id = newId("gvp-nt");
      box.appendChild(p);
      return p.id;
    });
    var row = el("div", "gvp-notice-actions");
    buttons.forEach(function (b) {
      var x = btn(b.primary ? "gvp-pill gvp-pill--primary" : "gvp-pill", b.label);
      if (ids.length) x.setAttribute("aria-describedby", ids.join(" "));
      x.addEventListener("click", function () { hideNotice(); b.run(); });
      row.appendChild(x);
    });
    box.appendChild(row);
    box.setAttribute("aria-labelledby", h.id);
    box.hidden = false;
    P.notice = { box: box, dismiss: onDismiss || function () {} };
    // after the slide's own announcement ("Slide 1 of 48: …"), in a region of its own
    var live = q("[data-gvp-notice-live]");
    if (live) {
      clear(live);
      setTimeout(function () { if (P.notice && P.notice.box === box) live.textContent = [title].concat(lines).join(" "); }, 600);
    }
  }
  function hideNotice() {
    if (!P.notice) return;
    P.notice.box.hidden = true;
    clear(P.notice.box);
    P.notice = null;
    var live = q("[data-gvp-notice-live]");
    if (live) clear(live);
    if (P.root && !P.root.contains(document.activeElement)) P.root.focus({ preventScroll: true });
  }
  function dismissNotice() {
    if (!P.notice) return;
    var d = P.notice.dismiss;
    hideNotice();
    d();
    if (P.root) P.root.focus({ preventScroll: true });
  }
  /** The blanks still empty on the slides (`stale`: how many slides the committee also changed since the
   *  presenter edited them — said here too, as one notice; `extra`: a further line). */
  function fillNotice(keys, stale, extra) {
    var defs = G.fillDefs(P.deck);
    var names = keys.map(function (k) { return defs[k] ? defs[k].label[LANG] || defs[k].label.en || k : k; });
    var shown = names.slice(0, 4).join(", ");
    var text = [names.length > 4 ? T("pres.blanks_text_more", { list: shown, n: names.length - 4 }) : T("pres.blanks_text", { list: shown })];
    var buttons = [{ label: T("pres.blanks_fill"), primary: true, run: function () { openDrawer("details"); } }];
    if (stale) {
      text.push(TN("pres.stale_also", stale));
      buttons.push({ label: T("pres.stale_review"), run: function () { openDrawer("slides"); } });
    }
    buttons.push({ label: T("pres.blanks_anyway"), run: function () { P.root.focus({ preventScroll: true }); } });
    notice(TN("pres.blanks_title", keys.length), text.concat(extra ? [extra] : []), buttons);
  }
  function staleNotice(n, extra) {
    notice(TN("pres.stale_title", n), [T("pres.stale_text")].concat(extra ? [extra] : []), [
      { label: T("pres.stale_review"), primary: true, run: function () { openDrawer("slides"); } },
      { label: T("pres.ok"), run: function () { P.root.focus({ preventScroll: true }); } },
    ]);
  }
  /** The browser stopped the presenter's second window: say so, and offer the presenter layout in this one. */
  function popupNotice(extra) {
    notice(T("pres.popup_h"), [T("pres.popup_text")].concat(extra ? [extra] : []), [
      { label: T("pres.presenter_here"), primary: true, run: function () { setMode("presenter"); } },
      { label: T("pres.cancel"), run: function () { P.root.focus({ preventScroll: true }); } },
    ]);
  }
  var TOAST = { el: null, timer: 0, left: 0, until: 0, action: null };
  /** The page's toast (outside the player): a polite live region that is there from the start, empty and out of
   *  sight until it has something to say (one created and filled at once is often not read out). */
  function pageToast() {
    var t = document.getElementById("gvp-page-toast");
    if (!t) {
      t = el("div", "gvp-toast gvp-toast--page is-idle");
      t.id = "gvp-page-toast";
      attrs(t, { role: "status", "aria-live": "polite" });
      document.body.appendChild(t);
    }
    return bindToast(t);
  }
  // While the pointer or the focus is on the toast its time stands still (Undo is not taken away from under
  // someone reaching for it); Esc puts it away.
  function bindToast(t) {
    if (!t || t.getAttribute("data-gvp-bound")) return t;
    t.setAttribute("data-gvp-bound", "");
    var pause = function () {
      if (!TOAST.timer || TOAST.el !== t) return;
      clearTimeout(TOAST.timer);
      TOAST.timer = 0;
      TOAST.left = Math.max(0, TOAST.until - Date.now());
    };
    var resume = function () {
      if (TOAST.timer || TOAST.el !== t || t.classList.contains("is-idle")) return;
      if (t.contains(document.activeElement) || t.matches(":hover")) return;
      armToast(t, Math.max(3000, TOAST.left));
    };
    t.addEventListener("focusin", pause);
    t.addEventListener("pointerenter", pause);
    t.addEventListener("focusout", function () { setTimeout(resume, 0); });
    t.addEventListener("pointerleave", resume);
    t.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !t.classList.contains("is-idle")) { e.preventDefault(); e.stopPropagation(); hideToast(t, true); }
    });
    return t;
  }
  function armToast(t, ms) {
    clearTimeout(TOAST.timer);
    TOAST.left = ms;
    TOAST.until = Date.now() + ms;
    TOAST.timer = setTimeout(function () { hideToast(t, true); }, ms);
  }
  /** Puts the toast away. `moveFocus`: when the focus was on it (Undo), it goes where the action says (`after`). */
  function hideToast(t, moveFocus) {
    clearTimeout(TOAST.timer);
    TOAST.timer = 0;
    var had = t.contains(document.activeElement);
    var a = TOAST.el === t ? TOAST.action : null;
    TOAST.action = null;
    clear(t);
    t.classList.add("is-idle");
    if (moveFocus && had && a && a.after) a.after();
  }
  /** A short message at the bottom (in the dialog while it is open), with an optional action (Undo) for 10 s;
   *  → the action's button (to focus). */
  function toast(text, action) {
    var t = P.root ? bindToast(q("[data-gvp-toast]")) : pageToast();
    if (!t) return null;
    clearTimeout(TOAST.timer);
    clear(t);
    var msg = el("span", "gvp-toast-text", text);
    msg.id = newId("gvp-tt");
    t.appendChild(msg);
    var focusIt = null;
    if (action) {
      var b = btn("gvp-toast-btn", action.label);
      b.setAttribute("aria-describedby", msg.id);
      b.addEventListener("click", function () {
        var had = t.contains(document.activeElement);
        hideToast(t, false);
        action.run();
        // the button is gone with its toast: the focus goes where the action says, not to the page's start
        if (had && (!document.activeElement || document.activeElement === document.body) && action.after) action.after();
      });
      t.appendChild(b);
      focusIt = b;
    }
    t.classList.remove("is-idle");
    TOAST.el = t;
    TOAST.action = action || null;
    armToast(t, action ? 10000 : 5000);
    return focusIt;
  }

  /* ------------------------------------------------------------------ full screen, black */
  function fsEl() { return document.fullscreenElement || document.webkitFullscreenElement || null; }
  function toggleFull() {
    if (!P.root) return;
    try {
      if (fsEl()) (document.exitFullscreen || document.webkitExitFullscreen).call(document);
      else (P.root.requestFullscreen || P.root.webkitRequestFullscreen).call(P.root);
    } catch (e) { /* not allowed here */ }
  }
  function syncFull() {
    qa('[data-gvp-act="full"]').forEach(function (b) {
      var lbl = b.querySelector(".gvp-btn-label, .sr-only, [data-gvp-full-label]");
      var txt = fsEl() ? T("pres.full_exit") : T("pres.full");
      if (lbl) lbl.textContent = txt;
      if (b.hasAttribute("title")) b.title = txt + " (F)";
    });
    onResize();
  }
  function setBlack(on, silent) {
    P.black = !!on;
    var blk = q("[data-gvp-black]");
    if (blk) blk.hidden = !P.black;
    var live = q("[data-gvp-live]");
    if (live) live.textContent = P.black ? T("pres.black_on") : T("pres.black_off");
    if (!silent) syncSend({ kind: "black", on: P.black });
  }

  /* ------------------------------------------------------------------ events of the dialog */
  function bindDialog() {
    P.root.addEventListener("click", onDialogClick);
    // on the document, not the dialog: a key pressed while the focus fell to <body> (a menu item or a button
    // that just disappeared) still works — the page behind is inert, so nothing else can have it
    document.addEventListener("keydown", onKey);
    var wrap = q("[data-gvp-stagewrap]");
    if (wrap) {
      wrap.addEventListener("click", onStageClick);
      wrap.addEventListener("pointerdown", onPointerDown);
      wrap.addEventListener("pointerup", onPointerUp);
      wrap.addEventListener("pointercancel", function () { swipe = null; });
    }
    var tabs = q("[data-gvp-tabs]");
    if (tabs) tabs.addEventListener("keydown", onTabKey);
    document.addEventListener("fullscreenchange", syncFull);
    document.addEventListener("webkitfullscreenchange", syncFull);
    document.addEventListener("pointerdown", onOutside, true);
    window.addEventListener("hashchange", onHash);
    if (!P.fullOk()) qa('[data-gvp-act="full"]').forEach(function (b) { b.hidden = true; });
  }
  P.fullOk = function () { return !!(document.documentElement.requestFullscreen || document.documentElement.webkitRequestFullscreen); };
  function unbindDialog() {
    document.removeEventListener("keydown", onKey);
    document.removeEventListener("fullscreenchange", syncFull);
    document.removeEventListener("webkitfullscreenchange", syncFull);
    document.removeEventListener("pointerdown", onOutside, true);
    window.removeEventListener("hashchange", onHash);
    window.removeEventListener("resize", onResize);
  }
  function onHash() {
    var n = slideFromHash(location.hash);
    if (n && P.cur && (!currentEntry() || currentEntry().n !== n)) go(n - 1, 0);
  }
  function onOutside(e) {
    if (P.menu && !P.menu.wrap.contains(e.target) && !P.menu.button.contains(e.target)) closeMenu();
  }
  function onDialogClick(e) {
    var t = e.target;
    if (!t.closest) return;
    var printItem = t.closest("[data-gvp-print-mode]");
    if (printItem) {
      closeMenu(true);
      // (a mouse click: the focus back on the dialog, so Space does not open the menu again — see below)
      if (e.detail > 0 && P.root) P.root.focus({ preventScroll: true });
      if (P.deck) printDeck(P.deck.id, printItem.getAttribute("data-gvp-print-mode"), printItem);
      return;
    }
    var a = t.closest("[data-gvp-act]");
    if (a && !a.disabled) {
      var name = a.getAttribute("data-gvp-act");
      if (a.getAttribute("role") === "menuitem") closeMenu(true);
      act(name, a);
      // a click with the mouse or a tap (not a key: detail 0) leaves the focus on the dialog when it is still on a
      // control bar's button — Space then turns the page (as a clicker does) instead of pressing that button again
      // (full screen off, notes off …). A menu, the overview or Customize keep the focus they took.
      if (e.detail > 0 && P.root && !P.menu) {
        var f = document.activeElement;
        if (f === a || (f && f.matches && f.matches("[data-gvp-act]") && f.closest(".gvp-bar, .gvp-pvbar, .gvp-top"))) P.root.focus({ preventScroll: true });
      }
      return;
    }
    var tab = t.closest("[data-gvp-tab]");
    if (tab) { selectTab(tab.getAttribute("data-gvp-tab"), true); return; }
    var th = t.closest(".gvp-thumb");
    if (th) {
      var i = Number(th.getAttribute("data-i"));
      closeOverview(false);
      go(i, 0, { announce: true });
      P.root.focus({ preventScroll: true });
    }
  }
  function act(name, src) {
    switch (name) {
      case "prev": if (P.preview) leavePreview(-1); else go(P.i - 1, -1); break;
      case "next": if (P.preview) leavePreview(1); else go(P.i + 1, 1); break;
      case "notes": setNotes(q("[data-gvp-notes]").hidden); break;
      case "overview": if (P.overview) closeOverview(); else openOverview(); break;
      case "customize": if (P.drawer) closeDrawer(); else openDrawer(P.tab || "slides"); break;
      case "presenter": openPresenter(); break;
      case "print": toggleMenu("print", src); break;
      case "more": toggleMenu("more", src); break;
      case "full": toggleFull(); break;
      case "black": setBlack(!P.black); break;
      case "close": closePlayer(); break;
      case "notes-smaller": VIEW.size = Math.max(0.8, Math.round((VIEW.size - 0.1) * 10) / 10); saveView(); renderNotesPanel(); break;
      case "notes-larger": VIEW.size = Math.min(2, Math.round((VIEW.size + 0.1) * 10) / 10); saveView(); renderNotesPanel(); break;
      case "timer-start": startTimer(); break;
      case "timer-pause": pauseTimer(); break;
      case "timer-reset": stopTimer(); break;
      default: break;
    }
  }
  /** From a previewed slide, the arrows go back into the show: to the nearest slide of the show that way. */
  function leavePreview(dir) {
    var e = P.preview;
    P.preview = null;
    var at = P.cur.list.indexOf(e);
    var target = -1;
    for (var k = at + dir; k >= 0 && k < P.cur.list.length && target < 0; k += dir) if (P.cur.list[k].shown) target = P.cur.list[k].n - 1;
    go(target < 0 ? P.i : target, dir);
  }
  // A swipe turns the page; the click a browser may send after it must not turn it again — but a swipe usually
  // sends none, so only a click right after the swipe is ignored (else the next real tap would be lost).
  var swipe = null, swipedAt = 0;
  function onPointerDown(e) { if (e.pointerType !== "mouse") swipe = { x: e.clientX, y: e.clientY }; }
  function onPointerUp(e) {
    if (!swipe) return;
    var dx = e.clientX - swipe.x, dy = e.clientY - swipe.y;
    swipe = null;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.3) {
      swipedAt = Date.now();
      act(dx < 0 ? "next" : "prev");
    }
  }
  function onStageClick(e) {
    if (Date.now() - swipedAt < 400) return;
    var t = e.target;
    if (!t.closest || t.closest("a, button, input, select, textarea, label, summary, [data-gvp-notice]")) return;
    if (!t.closest(".gvp-stage")) return;
    var sel = window.getSelection && window.getSelection();
    if (sel && String(sel).length) return;
    var r = q("[data-gvp-stagewrap]").getBoundingClientRect();
    act(e.clientX - r.left < r.width / 3 ? "prev" : "next");
  }
  function trapTab(e) {
    // a notice over the slide took no focus when it opened: from the dialog itself, Tab goes to its buttons first
    var a0 = document.activeElement;
    if (P.notice && !e.shiftKey && (a0 === P.root || !P.root.contains(a0))) {
      var nb = P.notice.box.querySelector("button");
      if (nb) { e.preventDefault(); nb.focus(); return; }
    }
    var f = qa('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex="0"], summary').filter(function (x) {
      return x.offsetParent !== null && !x.closest("[hidden]") && !x.closest("[inert]");
    });
    if (!f.length) { e.preventDefault(); return; }
    var first = f[0], last = f[f.length - 1];
    var a = document.activeElement;
    if (e.shiftKey && (a === first || a === P.root || !P.root.contains(a))) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && (a === last || !P.root.contains(a))) { e.preventDefault(); first.focus(); }
  }
  function escape() {
    if (P.digits) { P.digits = ""; showDigits(); return; }
    if (P.menu) { closeMenu(true); return; }
    if (P.notice) { dismissNotice(); return; }
    if (P.overview) { closeOverview(); return; }
    if (P.drawer) { closeDrawer(); return; }
    if (P.black) { setBlack(false); return; }
    closePlayer();
  }
  function showDigits() {
    var box = q("[data-gvp-digits]");
    if (!box) return;
    box.hidden = !P.digits;
    box.textContent = P.digits ? T("pres.go_to", { n: P.digits }) : "";
  }
  function onKey(e) {
    if (!P.root || e.altKey || e.ctrlKey || e.metaKey) return;
    var k = e.key, t = e.target;
    if (t && t !== document.body && t !== document.documentElement && !P.root.contains(t)) return;
    if (k === "Escape") { e.preventDefault(); escape(); return; }
    if (P.menu && P.menu.wrap.contains(t)) { menuKey(e); return; }
    if (k === "Tab") { trapTab(e); return; }
    if (!t.closest) return;
    if (t.closest("input, textarea, select, [contenteditable], [data-gvp-drawer], [data-gvp-toast]")) return;
    if (P.overview && t.closest("[data-gvp-overview]") && overviewKey(e)) return;
    var onControl = t.closest("a, button, summary");
    if ((k === " " || k === "Enter") && onControl && !P.digits) return;
    if (!P.cur) return;
    // a notice over the slide ("3 of your details are still blank") goes with the first key the player acts on:
    // the presenter has chosen to present (as "Present anyway"); a bare Shift (of Shift+Tab) leaves it
    if (P.notice && /^(?:Arrow(?:Right|Left|Up|Down)|Page(?:Up|Down)| |Home|End|[0-9nNoOcCpPfFbB.])$/.test(k)) hideNotice();
    if (/^[0-9]$/.test(k)) {
      e.preventDefault();
      P.digits = (P.digits + k).slice(0, 3);
      showDigits();
      clearTimeout(P.digitsTimer);
      P.digitsTimer = setTimeout(function () { P.digits = ""; showDigits(); }, 2500);
      return;
    }
    if (k === "Enter" && P.digits) {
      e.preventDefault();
      var n = Number(P.digits);
      P.digits = "";
      showDigits();
      if (n >= 1) go(n - 1, 0, { announce: true });
      return;
    }
    if (k === "Backspace" && P.digits) { e.preventDefault(); P.digits = P.digits.slice(0, -1); showDigits(); return; }
    var fwd = k === "ArrowDown" || k === "PageDown" || (k === " " && !e.shiftKey);
    var back = k === "ArrowUp" || k === "PageUp" || (k === " " && e.shiftKey);
    if ((fwd || back) && scrollSlide(fwd ? 1 : -1, k === "ArrowDown" || k === "ArrowUp")) { e.preventDefault(); return; }
    if (k === "ArrowRight" || fwd) { e.preventDefault(); act("next"); }
    else if (k === "ArrowLeft" || back) { e.preventDefault(); act("prev"); }
    else if (k === "Home") { e.preventDefault(); go(0, -1); }
    else if (k === "End") { e.preventDefault(); go(total() - 1, 1); }
    else if (k === "n" || k === "N") { e.preventDefault(); act("notes"); }
    else if (k === "o" || k === "O") { e.preventDefault(); act("overview"); }
    else if (k === "c" || k === "C") { e.preventDefault(); act("customize"); }
    else if (k === "p" || k === "P") { e.preventDefault(); act("presenter"); }
    else if (k === "f" || k === "F") { e.preventDefault(); toggleFull(); }
    else if (k === "b" || k === "B" || k === ".") { e.preventDefault(); setBlack(!P.black); }
  }

  /* ================================================================== 4. Customize (a drawer beside the stage)
     Version · Slides · Edit · Add · Your details · Prepare · Save & share. Every change is stored at once on this
     device and shown on the stage (the slide being edited is the one on the stage); nothing is sent anywhere. */
  var TABS = ["version", "slides", "edit", "add", "details", "prepare", "save"];
  function ds() { return P.deck ? G.deckState(STATE, P.deck.id) : null; }
  function openDrawer(tab) {
    if (!P.root) return;
    closeMenu();
    hideNotice();
    if (P.overview) closeOverview(false);
    var d = q("[data-gvp-drawer]");
    if (!d) return;
    d.hidden = false;
    P.drawer = "open";
    P.root.classList.add("has-drawer");
    selectTab(TABS.indexOf(tab) >= 0 ? tab : "slides", true);
    renderChrome();
    setUrl();
    onResize();
  }
  function closeDrawer() {
    flushEdits();
    var d = q("[data-gvp-drawer]");
    if (d) d.hidden = true;
    P.drawer = "";
    P.root.classList.remove("has-drawer");
    renderChrome();
    setUrl();
    onResize();
    var b = q('.gvp-bar [data-gvp-act="customize"]');
    if (b && b.offsetParent) b.focus({ preventScroll: true }); else P.root.focus({ preventScroll: true });
  }
  function selectTab(name, focusTab) {
    flushEdits();
    P.tab = name;
    qa("[data-gvp-tab]").forEach(function (t) {
      var on = t.getAttribute("data-gvp-tab") === name;
      t.setAttribute("aria-selected", on ? "true" : "false");
      t.tabIndex = on ? 0 : -1;
    });
    qa("[data-gvp-panel]").forEach(function (p) { p.hidden = p.getAttribute("data-gvp-panel") !== name; });
    renderPanel(name);
    if (focusTab) {
      var t = q('[data-gvp-tab="' + name + '"]');
      if (t) {
        t.focus({ preventScroll: true });
        // a short window (the drawer scrolls as one, its tabs with it): the focused tab in sight
        var d = q("[data-gvp-drawer]");
        if (d && d.scrollHeight > d.clientHeight + 1 && t.scrollIntoView) t.scrollIntoView({ block: "nearest" });
      }
    }
  }
  function onTabKey(e) {
    var t = e.target.closest && e.target.closest("[data-gvp-tab]");
    if (!t) return;
    var tabs = qa("[data-gvp-tab]");
    var at = tabs.indexOf(t), to = -1;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") to = (at + 1) % tabs.length;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") to = (at - 1 + tabs.length) % tabs.length;
    else if (e.key === "Home") to = 0;
    else if (e.key === "End") to = tabs.length - 1;
    if (to < 0) return;
    e.preventDefault();
    selectTab(tabs[to].getAttribute("data-gvp-tab"), true);
  }
  function panel(name) { return q('[data-gvp-panel="' + name + '"]'); }
  function renderPanel(name) {
    if (!P.cur || !P.drawer) return;
    var p = panel(name);
    if (!p) return;
    keepFocus(p, function () {
      clear(p);
      if (name === "version") panelVersion(p);
      else if (name === "slides") panelSlides(p);
      else if (name === "edit") panelEdit(p);
      else if (name === "add") panelAdd(p);
      else if (name === "details") panelDetails(p);
      else if (name === "prepare") panelPrepare(p);
      else if (name === "save") panelSave(p);
    });
  }
  /** Redraws a panel and puts the focus back on the same control (its data-gvp-key), so a switch or a Move
   *  button keeps the focus after the list is drawn again; the list stays where it was scrolled, then shows what
   *  the panel asked to show (REVEAL: the current slide's row). */
  var REVEAL = null;
  function keepFocus(p, draw) {
    var a = document.activeElement;
    var key = a && p.contains(a) ? a.getAttribute("data-gvp-key") : null;
    var scroll = p.scrollTop;
    REVEAL = null;
    draw();
    p.scrollTop = scroll;
    if (REVEAL) { REVEAL.scrollIntoView({ block: "nearest" }); REVEAL = null; }
    if (key) {
      var again = p.querySelector('[data-gvp-key="' + key + '"]');
      if (again && !again.disabled) again.focus({ preventScroll: true });
      else if (again) {
        var row = again.closest("[data-id]");
        var other = row && row.querySelector("button:not([disabled])");
        (other || p).focus({ preventScroll: true });
      }
    }
  }
  /** The current slide changed: the panels about "this slide" follow it. */
  function drawerFollow(moved) {
    if (!P.drawer || !moved) return;
    if (P.tab === "edit" || P.tab === "add" || P.tab === "slides") renderPanel(P.tab);
  }
  /** After a change of the presenter's version: store it, recompute, redraw what shows it. */
  function changed(opts) {
    opts = opts || {};
    touch(ds());
    saveState();
    refresh();
    renderStage(0);
    renderChrome();
    renderNotesPanel();
    if (P.mode === "presenter") renderPresenter();
    setUrl();
    if (opts.panel !== false && P.drawer) renderPanel(P.tab);
    syncSend({ kind: "state" });
  }
  function heading(p, text, extra) {
    var head = el("div", "gvp-ph");
    head.appendChild(el("h4", "gvp-ph-h", text));
    if (extra) head.appendChild(extra);
    p.appendChild(head);
    return head;
  }
  function para(p, text, cls) { var x = el("p", cls || "gvp-pp", text); p.appendChild(x); return x; }
  function titleOf(e) { return plainText(e.slide.title, ctxFor(P.cur, "slide")); }
  /** A slide's title among the controls: marked with the slide's language when the page's differs. */
  function langOf(node, e) {
    var l = (e && e.slide && e.slide.lang) || "en";
    if (l !== LANG) node.setAttribute("lang", l);
    return node;
  }
  function about(min) { return Math.max(1, Math.round(min)); }

  /* ---------- Version ---------- */
  function panelVersion(p) {
    heading(p, T("pres.tab_version"));
    para(p, T("pres.version_intro"));
    var fs = el("fieldset", "gvp-radios");
    fs.appendChild(el("legend", "sr-only", T("pres.tab_version")));
    var first = P.deck.presets[0] ? P.deck.presets[0].id : "";
    P.deck.presets.forEach(function (pr) {
      var c = G.current(P.deck, STATE, pr.id, P.cur.nowMs);
      var lab = el("label", "gvp-radio");
      var input = el("input");
      input.type = "radio";
      input.name = "gvp-preset";
      input.value = pr.id;
      input.checked = P.cur.preset.id === pr.id;
      input.setAttribute("data-gvp-key", "preset:" + pr.id);
      input.addEventListener("change", function () {
        ds().preset = pr.id === first ? "" : pr.id;
        changed();
        var live = q("[data-gvp-live]");
        if (live) live.textContent = T("pres.version_set", { label: pr.label[LANG] || pr.label.en });
      });
      lab.appendChild(input);
      var words = el("span", "gvp-radio-words");
      words.appendChild(el("span", "gvp-radio-title", pr.label[LANG] || pr.label.en || pr.id));
      words.appendChild(el("span", "gvp-radio-sub", T("pres.version_len", { n: c.shown.length, min: about(c.total) })));
      if (pr.note) words.appendChild(el("span", "gvp-radio-note", pr.note[LANG] || pr.note.en || ""));
      lab.appendChild(words);
      fs.appendChild(lab);
    });
    p.appendChild(fs);
    var sum = G.summary(ds(), P.deck);
    var mine = sum.hidden + sum.shown + sum.added;
    para(p, T("pres.version_now", { n: total(), min: about(P.cur.total) }) + (mine ? " " + T("pres.version_mine") : ""), "gvp-pp gvp-pp--strong");
  }

  /* ---------- Slides ---------- */
  function badge(text, cls) { return el("span", "gvp-badge" + (cls ? " " + cls : ""), text); }
  function panelSlides(p) {
    var tools = el("div", "gvp-ph-tools");
    var all = btn("gvp-pill gvp-pill--sm", T("pres.show_all"));
    all.setAttribute("data-gvp-key", "show-all");
    all.addEventListener("click", function () {
      var undo = snapshot();
      G.showAll(P.cur);
      changed();
      toast(T("pres.all_shown"), undoAction(undo));
    });
    var orig = btn("gvp-pill gvp-pill--sm", T("pres.original_order"));
    orig.setAttribute("data-gvp-key", "orig-order");
    orig.disabled = !ds().order;
    orig.addEventListener("click", function () {
      var undo = snapshot();
      G.originalOrder(ds());
      changed();
      toast(T("pres.order_back"), undoAction(undo));
    });
    tools.appendChild(all);
    tools.appendChild(orig);
    heading(p, T("pres.tab_slides"), tools);
    para(p, T("pres.slides_intro"));
    var ol = el("ol", "gvp-rows");
    var curE = currentEntry();
    P.cur.list.forEach(function (e, idx) {
      var li = el("li", "gvp-row" + (e === curE ? " is-current" : "") + (e.shown ? "" : " is-off"));
      li.setAttribute("data-id", e.id);
      var handle = el("span", "gvp-handle");
      attrs(handle, { "aria-hidden": "true", title: T("pres.drag") });
      handle.appendChild(icon("grip-vertical"));
      handle.addEventListener("pointerdown", function (ev) { startDrag(ev, li, e); });
      li.appendChild(handle);
      li.appendChild(el("span", "gvp-row-n", e.shown ? String(e.n) : "–"));
      var tb = btn("gvp-row-title", null);
      tb.setAttribute("data-gvp-key", "title:" + e.id);
      if (e === curE) tb.setAttribute("aria-current", "true");
      tb.appendChild(langOf(el("span", "gvp-row-t", titleOf(e)), e));
      if (e.slide.part && e.slide.part.title) tb.appendChild(tInto(el("span", "gvp-row-sub"), "pres.part", { n: e.slide.part.n, title: e.slide.part.title }, ["title"]));
      tb.addEventListener("click", function () { goToId(e.id, {}); });
      li.appendChild(tb);
      var bs = el("span", "gvp-badges");
      if (e.slide.optional) bs.appendChild(badge(T("pres.b_optional")));
      if (e.added) bs.appendChild(badge(T("pres.b_yours"), "is-yours"));
      else if (e.edited.length) bs.appendChild(badge(T("pres.b_edited"), "is-edited"));
      if (e.stale) bs.appendChild(badge(T("pres.b_updated"), "is-updated"));
      if (e.why === "facilitator") bs.appendChild(badge(T("pres.b_facilitator")));
      if (e.why === "window") bs.appendChild(badge(T("pres.b_not_today")));
      if (e.slide.handout) bs.appendChild(badge(T("pres.b_handout")));
      if (bs.children.length) li.appendChild(bs);
      if (e.why !== "facilitator") {
        var sw = btn("gvp-switch", null);
        attrs(sw, { role: "switch", "aria-checked": e.shown ? "true" : "false", "data-gvp-key": "sw:" + e.id });
        // named by its content, not aria-label: "Mostrar «<span lang="en">Welcome</span>»" keeps the title English
        sw.appendChild(tInto(el("span", "sr-only"), "pres.switch_label", { title: titleOf(e) }, ["title"], e.slide.lang));
        sw.appendChild(attrs(el("span", "gvp-switch-track"), { "aria-hidden": "true" }));
        if (e.why === "window") { sw.disabled = true; sw.title = T("pres.why_window"); }
        sw.addEventListener("click", function () {
          G.setShown(P.cur, e.id, !e.shown);
          changed();
        });
        li.appendChild(sw);
      }
      if (e === curE) {
        var acts = el("div", "gvp-row-acts");
        var up = btn("gvp-pill gvp-pill--sm", T("pres.move_up"), { icon: "arrow-up" });
        up.setAttribute("data-gvp-key", "up:" + e.id);
        up.disabled = idx === 0;
        up.addEventListener("click", function () { moveBy(e, -1); });
        var down = btn("gvp-pill gvp-pill--sm", T("pres.move_down"), { icon: "arrow-down" });
        down.setAttribute("data-gvp-key", "down:" + e.id);
        down.disabled = idx === P.cur.list.length - 1;
        down.addEventListener("click", function () { moveBy(e, 1); });
        var ed = btn("gvp-pill gvp-pill--sm", T("pres.edit"), { icon: "pencil" });
        ed.addEventListener("click", function () { selectTab("edit", true); });
        acts.appendChild(up);
        acts.appendChild(down);
        acts.appendChild(ed);
        if (e.added || e.edited.length) {
          var rs = btn("gvp-pill gvp-pill--sm", e.added ? T("pres.delete_slide") : T("pres.reset_slide"), { icon: e.added ? "trash-2" : "rotate-ccw" });
          rs.addEventListener("click", function () { resetOne(e); });
          acts.appendChild(rs);
        }
        li.appendChild(acts);
      }
      ol.appendChild(li);
    });
    p.appendChild(ol);
    // the current slide's row in sight (keepFocus scrolls to it once the list is back where it was) — only where the
    // list scrolls by itself: in a short window the whole drawer scrolls, and moving it there would take the
    // focused tab (or control) out of sight
    var cur = p.querySelector(".gvp-row.is-current");
    if (cur && cur.scrollIntoView && p.scrollHeight > p.clientHeight + 1 && !p.contains(document.activeElement)) REVEAL = cur;
  }
  function moveBy(e, delta) {
    var to = G.move(P.cur, e.id, delta);
    changed();
    var live = q("[data-gvp-live]");
    if (live) live.textContent = T("pres.moved", { n: to + 1, total: P.cur.list.length });
  }
  function resetOne(e) {
    if (e.added && !window.confirm(T("pres.delete_confirm", { title: titleOf(e) }))) return;
    var undo = snapshot();
    G.resetSlide(ds(), e.id);
    changed();
    // the button pressed is gone (or disabled) with the redrawn panel: the focus goes to Undo, as after a reset
    var b = toast(e.added ? T("pres.deleted") : T("pres.slide_reset"), undoAction(undo));
    if (b && (!document.activeElement || document.activeElement === document.body || !P.root.contains(document.activeElement) || document.activeElement.disabled)) b.focus();
  }
  /** Drag a slide by its handle (a pointer; the keyboard has Move up / Move down). */
  function startDrag(ev, li, e) {
    if (ev.button !== undefined && ev.button !== 0) return;
    ev.preventDefault();
    var list = li.parentNode;
    var rows = Array.prototype.slice.call(list.children);
    var from = rows.indexOf(li);
    var to = from;
    var marker = el("li", "gvp-drop");
    marker.setAttribute("aria-hidden", "true");
    li.classList.add("is-dragging");
    var scroller = list.closest("[data-gvp-panel]");
    var handle = ev.currentTarget;
    try { handle.setPointerCapture(ev.pointerId); } catch (err) { /* fine */ }
    function onMove(m) {
      var y = m.clientY;
      to = rows.length;
      for (var i = 0; i < rows.length; i++) {
        var r = rows[i].getBoundingClientRect();
        if (y < r.top + r.height / 2) { to = i; break; }
      }
      if (to === rows.length) list.appendChild(marker); else list.insertBefore(marker, rows[to]);
      if (scroller) {
        var sr = scroller.getBoundingClientRect();
        if (y < sr.top + 40) scroller.scrollTop -= 12;
        else if (y > sr.bottom - 40) scroller.scrollTop += 12;
      }
    }
    function onUp() {
      handle.removeEventListener("pointermove", onMove);
      handle.removeEventListener("pointerup", onUp);
      handle.removeEventListener("pointercancel", onUp);
      li.classList.remove("is-dragging");
      if (marker.parentNode) marker.parentNode.removeChild(marker);
      var dest = to > from ? to - 1 : to;
      if (dest !== from) {
        G.move(P.cur, e.id, 0, dest);
        changed();
        var live = q("[data-gvp-live]");
        if (live) live.textContent = T("pres.moved", { n: dest + 1, total: P.cur.list.length });
      }
    }
    handle.addEventListener("pointermove", onMove);
    handle.addEventListener("pointerup", onUp);
    handle.addEventListener("pointercancel", onUp);
  }
  /** The deck's stored part as it is now, and an Undo that puts it back. */
  function snapshot() {
    var id = P.deck.id;
    return { id: id, ds: JSON.parse(JSON.stringify(G.deckState(STATE, id))) };
  }
  function undoAction(snap, extra) {
    return {
      label: T("pres.undo"),
      run: function () {
        G.restoreDeck(STATE, snap.id, snap.ds);
        if (extra) extra();
        saveState();
        if (P.root && P.deck && P.deck.id === snap.id) {
          refresh();
          renderStage(0); renderChrome(); renderNotesPanel();
          if (P.mode === "presenter") renderPresenter();
          if (P.drawer) renderPanel(P.tab);
          syncSend({ kind: "state" });
        }
        toast(T("pres.undone"));
      },
      after: function () { if (P.root) P.root.focus({ preventScroll: true }); },
    };
  }

  /* ---------- Edit ---------- */
  var EDIT = { timer: 0, pending: null };
  function flushEdits() {
    if (EDIT.timer) { clearTimeout(EDIT.timer); EDIT.timer = 0; }
    if (EDIT.pending) { var f = EDIT.pending; EDIT.pending = null; f(); }
  }
  function later(fn) {
    EDIT.pending = fn;
    clearTimeout(EDIT.timer);
    EDIT.timer = setTimeout(function () { EDIT.timer = 0; flushEdits(); }, 280);
  }
  /** Stores one field and shows it on the stage — the form itself is not redrawn (the cursor stays). Equal to what
   *  the slide says in the version being shown, the field is no edit (presentations-core.js setField). */
  function commit(e, field, value) {
    G.setField(P.deck, ds(), e.id, field, value, P.cur && P.cur.preset ? P.cur.preset.id : "");
    touch(ds());
    saveState();
    refresh();
    renderStage(0);
    renderChrome();
    renderNotesPanel();
    if (P.mode === "presenter") renderPresenter();
    syncSend({ kind: "state" });
    var ep = panel("edit");
    var head = ep && ep.querySelector("[data-gvp-edit-state]");
    var now = P.cur.byId[e.id];
    if (head && now) head.hidden = !(now.edited.length || now.added);
    // "Reset this slide" as soon as there is something to reset (not only when the panel is drawn again)
    var rs = ep && ep.querySelector("[data-gvp-edit-reset]");
    if (rs && now && !now.added) rs.disabled = !now.edited.length;
    longWarning();
  }
  var HINTS = { list: "pres.hint_list", outline: "pres.hint_outline", cells: "pres.hint_cells", table: "pres.hint_table", links: "pres.hint_links", flow: "pres.hint_flow" };
  var FIELD_LABEL = {
    title: "pres.f_title", eyebrow: "pres.f_eyebrow", subtitle: "pres.f_subtitle", lines: "pres.f_lines", number: "pres.f_number",
    items: "pres.f_items", columns: "pres.f_columns", header: "pres.f_header", rows: "pres.f_rows", quote: "pres.f_quote",
    credit: "pres.f_credit", steps: "pres.f_steps", duration: "pres.f_duration", materials: "pres.f_materials",
    prompts: "pres.f_prompts", note: "pres.f_note", links: "pres.f_links", sources: "pres.f_sources", message: "pres.f_message",
    body: "pres.f_body", intro: "pres.f_intro", takeaway: "pres.f_takeaway", source: "pres.f_source", minutes: "pres.f_minutes",
    notes: "pres.f_notes",
  };
  function fieldBox(labelText, control, hint, mark) {
    var box = el("div", "gvp-field");
    var id = control.id || (control.id = newId("gvp-f"));
    var lab = el("label", "gvp-label", labelText);
    lab.htmlFor = id;
    if (mark) { lab.appendChild(document.createTextNode(" ")); lab.appendChild(mark); }
    box.appendChild(lab);
    if (hint) {
      var h = el("p", "gvp-hint", hint);
      h.id = newId("gvp-h");
      control.setAttribute("aria-describedby", h.id);
      box.appendChild(h);
    }
    box.appendChild(control);
    return box;
  }
  function textControl(kind, value) {
    var multi = kind !== "line" && kind !== "num" && kind !== "cells";
    var c = el(multi ? "textarea" : "input", "gvp-input" + (multi ? " gvp-textarea" : ""));
    if (!multi) c.type = kind === "num" ? "number" : "text";
    if (kind === "num") { c.step = "0.25"; c.min = "0"; c.inputMode = "decimal"; }
    c.value = value;
    if (multi) c.rows = Math.min(12, Math.max(2, String(value).split("\n").length + 1, Math.ceil(String(value).length / 46)));
    c.setAttribute("spellcheck", "true");
    c.setAttribute("lang", "en");
    return c;
  }
  function panelEdit(p) {
    var e = currentEntry();
    if (!e) return;
    var s = e.slide;
    var h = heading(p, e.shown ? T("pres.edit_h", { n: e.n }) : T("pres.edit_h_off"));
    var state = el("span", "gvp-badge is-edited", e.added ? T("pres.b_yours") : T("pres.b_edited"));
    state.setAttribute("data-gvp-edit-state", "");
    state.hidden = !(e.edited.length || e.added);
    h.appendChild(state);
    langOf(para(p, titleOf(e), "gvp-pp gvp-pp--strong"), e);
    if (e.stale) {
      var warn = el("div", "gvp-warn");
      warn.appendChild(el("p", "gvp-warn-h", T("pres.stale_one")));
      warn.appendChild(el("p", "", T("pres.stale_one_text")));
      var row = el("div", "gvp-warn-acts");
      var useNew = btn("gvp-pill", T("pres.use_new"));
      useNew.addEventListener("click", function () {
        var undo = snapshot();
        G.dropEdit(ds(), e.id);
        changed();
        toast(T("pres.slide_reset"), undoAction(undo));
      });
      var keep = btn("gvp-pill", T("pres.keep_mine"));
      keep.addEventListener("click", function () { G.keepEdit(P.deck, ds(), e.id); changed(); });
      row.appendChild(useNew);
      row.appendChild(keep);
      warn.appendChild(row);
      p.appendChild(warn);
    }
    var lw = el("p", "gvp-warn gvp-warn--long", T("pres.slide_long"));
    lw.setAttribute("data-gvp-long", "");
    lw.hidden = true;
    p.appendChild(lw);
    para(p, T("pres.edit_help"), "gvp-pp gvp-pp--muted");
    // a field the slide has words of its own for in some version (an agenda, an activity's time): the edit stays
    // in this version (presentations-core.js setField) — its label names the version
    var src = e.added ? null : P.deck.slides.filter(function (x) { return x.id === e.id; })[0];
    var versionMark = function (field) {
      var pr = P.cur.preset;
      if (!src || !G.versioned(src, field) || !pr || !pr.label) return null;
      return badge(T("pres.version_set", { label: pr.label[LANG] || pr.label.en || pr.id }), "is-version");
    };
    var form = el("form", "gvp-form");
    form.addEventListener("submit", function (ev) { ev.preventDefault(); });
    G.fieldsOf(s.layout).forEach(function (f) {
      var field = f[0], kind = f[1];
      if (field === "minutes" && s.facilitator) return;
      var label = T(FIELD_LABEL[field] || "pres.f_title");
      if (kind === "columns") { form.appendChild(columnsEditor(e, versionMark(field))); return; }
      if (kind === "agenda") { form.appendChild(agendaEditor(e, versionMark(field))); return; }
      var v = s[field];
      if (field === "minutes") v = e.added || e.edited.indexOf("minutes") >= 0 ? s.minutes : G.minutesOf(e, P.cur.preset.id);
      var c = textControl(kind, G.toText(kind, v === undefined || v === null ? "" : v));
      c.setAttribute("data-gvp-key", "f:" + field);
      var hint = HINTS[kind] ? T(HINTS[kind]) : field === "minutes" ? T("pres.hint_minutes") : "";
      c.addEventListener("input", function () {
        later(function () {
          var val = G.fromText(kind, c.value);
          // an empty optional field is a field left out; the title stays (an empty one shows nothing)
          if ((val === "" || (Array.isArray(val) && !val.length)) && field !== "title" && field !== "notes") val = kind === "line" || kind === "text" ? "" : [];
          commit(e, field, val === undefined ? null : val);
        });
      });
      c.addEventListener("blur", flushEdits);
      form.appendChild(fieldBox(label, c, hint, versionMark(field)));
    });
    p.appendChild(form);
    var foot = el("div", "gvp-ph-tools gvp-ph-tools--end");
    if (e.added) {
      var del = btn("gvp-pill", T("pres.delete_slide"), { icon: "trash-2" });
      del.addEventListener("click", function () { resetOne(e); });
      foot.appendChild(del);
    } else {
      var rs = btn("gvp-pill", T("pres.reset_slide"), { icon: "rotate-ccw" });
      rs.setAttribute("data-gvp-edit-reset", "");
      rs.disabled = !e.edited.length;
      rs.addEventListener("click", function () { flushEdits(); resetOne(P.cur.byId[e.id] || e); });
      foot.appendChild(rs);
    }
    p.appendChild(foot);
    longWarning();
  }
  /** Edit: a slide too long to fit even at the smallest type scrolls on the screen — say so, before it is printed
   *  that way (paper shrinks it further, but not without end). */
  function longWarning() {
    var ep = panel("edit");
    var w = ep && ep.querySelector("[data-gvp-long]");
    if (!w) return;
    var sl = q("[data-gvp-stage] .gvp-slide");
    w.hidden = !(sl && sl.classList.contains("is-scroll"));
  }
  /** A legend for a group of fields, with the version's mark when the edit stays in the version (panelEdit). */
  function legend(text, mark) {
    var lg = el("legend", "gvp-label", text);
    if (mark) { lg.appendChild(document.createTextNode(" ")); lg.appendChild(mark); }
    return lg;
  }
  function columnsEditor(e, mark) {
    var cols = JSON.parse(JSON.stringify(e.slide.columns || []));
    var fs = el("fieldset", "gvp-fieldset");
    fs.appendChild(legend(T("pres.f_columns"), mark));
    cols.forEach(function (c, i) {
      var box = el("div", "gvp-subfields");
      box.appendChild(el("p", "gvp-sublabel", T("pres.column_n", { n: i + 1 })));
      var head = textControl("line", c.heading || "");
      head.setAttribute("data-gvp-key", "col" + i + ":heading");
      box.appendChild(fieldBox(T("pres.f_heading"), head));
      var content = c.items ? textControl("outline", G.toText("outline", c.items)) : textControl("text", c.text || "");
      content.setAttribute("data-gvp-key", "col" + i + ":content");
      box.appendChild(fieldBox(c.items ? T("pres.f_items") : T("pres.f_text"), content, c.items ? T("pres.hint_outline") : ""));
      var upd = function () {
        later(function () {
          var next = JSON.parse(JSON.stringify(cols));
          next[i].heading = G.fromText("line", head.value);
          if (c.items) next[i].items = G.fromText("outline", content.value);
          else next[i].text = G.fromText("text", content.value);
          cols = next;
          commit(e, "columns", next);
        });
      };
      head.addEventListener("input", upd);
      content.addEventListener("input", upd);
      head.addEventListener("blur", flushEdits);
      content.addEventListener("blur", flushEdits);
      fs.appendChild(box);
    });
    return fs;
  }
  function agendaEditor(e, mark) {
    var fs = el("fieldset", "gvp-fieldset");
    fs.appendChild(legend(T("pres.f_agenda"), mark));
    fs.appendChild(el("p", "gvp-hint", T("pres.hint_agenda")));
    var list = el("div", "gvp-agenda-rows");
    fs.appendChild(list);
    var editedItems = e.edited.indexOf("items") >= 0;
    var rows = G.agendaRows(e, P.cur, { all: true }).map(function (r) {
      // a row with `from` shows an empty time ("automatic", its computed time as the placeholder) unless the
      // presenter typed one
      return { time: r.from ? (editedItems && !r.auto ? r.time : "") : r.time, title: r.title, detail: r.detail, from: r.from, computed: r.computed };
    });
    function save() {
      later(function () {
        var out = rows.map(function (r) {
          var o = { time: r.time, title: r.title };
          if (r.detail) o.detail = r.detail;
          if (r.from) o.from = r.from;
          return o;
        });
        // back to what the version's agenda says (a time typed and cleared again): no edit is left behind
        var src = !e.added && P.deck.slides.filter(function (s) { return s.id === e.id; })[0];
        var own = src ? G.versionValue(src, "items", P.cur.preset.id) : null;
        commit(e, "items", own && G.agendaUnchanged(out, own) ? null : out);
      });
    }
    function draw() {
      clear(list);
      rows.forEach(function (r, i) {
        var line = el("div", "gvp-agenda-row");
        var t = textControl("line", r.time);
        t.className += " gvp-input--time";
        t.placeholder = r.from ? (r.computed ? T("pres.auto_time", { time: r.computed }) : T("pres.left_out_short")) : "";
        t.setAttribute("aria-label", T("pres.agenda_time", { n: i + 1 }));
        t.setAttribute("data-gvp-key", "ag" + i + ":time");
        var ti = textControl("line", r.title);
        ti.setAttribute("aria-label", T("pres.agenda_title", { n: i + 1 }));
        ti.setAttribute("data-gvp-key", "ag" + i + ":title");
        var de = textControl("line", r.detail || "");
        de.setAttribute("aria-label", T("pres.agenda_detail", { n: i + 1 }));
        de.setAttribute("data-gvp-key", "ag" + i + ":detail");
        de.placeholder = T("pres.agenda_detail_ph");
        [t, ti, de].forEach(function (c, k) {
          c.addEventListener("input", function () { rows[i][["time", "title", "detail"][k]] = c.value; save(); });
          c.addEventListener("blur", flushEdits);
        });
        var rm = btn("gvp-iconbtn", T("pres.agenda_remove", { n: i + 1 }), { icon: "x", hideLabel: true });
        rm.addEventListener("click", function () { rows.splice(i, 1); draw(); save(); flushEdits(); });
        line.appendChild(t);
        line.appendChild(ti);
        line.appendChild(de);
        line.appendChild(rm);
        list.appendChild(line);
      });
    }
    draw();
    var add = btn("gvp-pill gvp-pill--sm", T("pres.agenda_add"), { icon: "plus" });
    add.addEventListener("click", function () {
      rows.push({ time: "", title: "", detail: "", from: "" });
      draw();
      var inputs = list.querySelectorAll("input");
      if (inputs.length) inputs[inputs.length - 3].focus();
    });
    fs.appendChild(add);
    return fs;
  }

  /* ---------- Add a slide ---------- */
  var ADD_KINDS = [
    ["bullets", "list", "pres.add_bullets", "pres.add_bullets_d"],
    ["text", "text", "pres.add_text", "pres.add_text_d"],
    ["section", "bookmark", "pres.add_section", "pres.add_section_d"],
    ["qa", "message-circle-question", "pres.add_qa", "pres.add_qa_d"],
  ];
  function panelAdd(p) {
    var e = currentEntry();
    heading(p, T("pres.tab_add"));
    var where = p.appendChild(el("p", "gvp-pp"));
    if (e) tInto(where, e.shown ? "pres.add_after" : "pres.add_after_off", { n: e.n, title: titleOf(e) }, ["title"], e.slide.lang);
    else where.textContent = T("pres.add_end");
    var grid = el("div", "gvp-addgrid");
    ADD_KINDS.forEach(function (k) {
      var b = btn("gvp-addbtn", null);
      b.appendChild(icon(k[1]));
      var w = el("span", "gvp-addwords");
      w.appendChild(el("span", "gvp-addtitle", T(k[2])));
      w.appendChild(el("span", "gvp-adddesc", T(k[3])));
      b.appendChild(w);
      b.addEventListener("click", function () {
        var id = G.addSlide(P.deck, ds(), k[0], e ? e.id : "");
        if (!id) { toast(T("pres.add_full")); return; }
        touch(ds());
        saveState();
        refresh();
        goToId(id, {});
        selectTab("edit", false);
        var first = panel("edit").querySelector('[data-gvp-key="f:title"]');
        if (first) { first.focus(); first.select(); }
        var live = q("[data-gvp-live]");
        if (live) live.textContent = T("pres.added");
        syncSend({ kind: "state" });
      });
      grid.appendChild(b);
    });
    p.appendChild(grid);
    para(p, T("pres.add_note"), "gvp-pp gvp-pp--muted");
  }

  /* ---------- Your details ---------- */
  function panelDetails(p) {
    var defs = G.fillDefs(P.deck);
    var keys = Object.keys(defs);
    var empty = keys.filter(function (k) { return !G.fillValue(P.deck, STATE, k); });
    heading(p, T("pres.tab_details"));
    para(p, T("pres.details_intro"));
    para(p, empty.length ? TN("pres.details_empty", empty.length) : T("pres.details_done"), "gvp-pp gvp-pp--strong").setAttribute("data-gvp-blanks", "");
    var groups = G.fillGroups(P.cur);
    groups.forEach(function (g, gi) {
      var det = el("details", "gvp-group");
      var missing = g.keys.filter(function (k) { return empty.indexOf(k) >= 0; }).length;
      det.open = gi < 2 || (missing > 0 && groups.length <= 6);
      var sum = el("summary", "gvp-group-sum");
      var gt = sum.appendChild(el("span", "gvp-group-t"));
      if (g.entry) tInto(gt, g.entry.shown ? "pres.details_group" : "pres.details_group_off", { n: g.entry.n, title: titleOf(g.entry) }, ["title"], g.entry.slide.lang);
      else gt.textContent = T("pres.details_other");
      var cnt = el("span", "gvp-group-n", T("pres.details_count", { n: g.keys.length - missing, total: g.keys.length }));
      cnt.setAttribute("data-gvp-keys", g.keys.join(" "));
      sum.appendChild(cnt);
      det.appendChild(sum);
      g.keys.forEach(function (key) {
        var def = defs[key];
        // where the value lives, looked up again when it is stored (the state may have been read anew since)
        var storeOf = function () { return def.shared ? STATE.shared.fill : ds().fill; };
        var store = storeOf();
        var c = textControl("line", Object.prototype.hasOwnProperty.call(store, key) ? store[key] : "");
        c.placeholder = def.default || def.hint || "";
        c.setAttribute("data-gvp-key", "fill:" + key);
        c.removeAttribute("lang");
        var hint = [];
        if (def.shared) hint.push(T("pres.details_shared"));
        if (def.notes_only) hint.push(T("pres.details_notes_only"));
        if (def.default) hint.push(T("pres.details_default", { value: def.default }));
        else if (def.hint) hint.push(T(def.notes_only ? "pres.details_hint_notes" : "pres.details_hint", { hint: def.hint }));
        c.addEventListener("input", function () {
          later(function () {
            var v = c.value.replace(/[\uE000\uE001]/g, "");
            var target = storeOf();
            if (v.trim()) target[key] = v; else delete target[key];
            touch(ds());
            saveState();
            refresh();
            renderStage(0);
            renderNotesPanel();
            if (P.mode === "presenter") renderPresenter();
            syncSend({ kind: "state" });
            detailCounts(p);
          });
        });
        c.addEventListener("blur", flushEdits);
        det.appendChild(fieldBox((def.label && (def.label[LANG] || def.label.en)) || key, c, hint.join(" ")));
      });
      p.appendChild(det);
    });
  }

  /** The counts of Your details ("3 still blank", "2 of 4 filled in"), redrawn in place while typing. */
  function detailCounts(p) {
    var keys = Object.keys(G.fillDefs(P.deck));
    var empty = keys.filter(function (k) { return !G.fillValue(P.deck, STATE, k); });
    var top = p.querySelector("[data-gvp-blanks]");
    if (top) top.textContent = empty.length ? TN("pres.details_empty", empty.length) : T("pres.details_done");
    Array.prototype.forEach.call(p.querySelectorAll("[data-gvp-keys]"), function (n) {
      var ks = n.getAttribute("data-gvp-keys").split(" ");
      var missing = ks.filter(function (k) { return empty.indexOf(k) >= 0; }).length;
      n.textContent = T("pres.details_count", { n: ks.length - missing, total: ks.length });
    });
  }

  /* ---------- Prepare ---------- */
  /** Prepare: every page for the facilitator (the "For facilitators" / "For the chair" dividers too, with their
   *  notes: what to read first), in the deck's order, and the participants' handouts — each one can be viewed and
   *  printed, and so can all of them at once (the handouts alone, for the room). */
  function panelPrepare(p) {
    var pages = P.cur.list.filter(function (e) { return e.slide.facilitator || e.slide.handout; });
    var fac = pages.filter(function (e) { return e.slide.facilitator; });
    var handouts = pages.filter(function (e) { return e.slide.handout; });
    var tools = el("div", "gvp-ph-tools");
    var printAll = function (key, list) {
      var b = btn("gvp-pill gvp-pill--sm", TN(key, list.length), { icon: "printer" });
      b.addEventListener("click", function () { printDeck(P.deck.id, "pages", b, list.map(function (e) { return e.id; })); });
      tools.appendChild(b);
    };
    // (a single page has its own Print below)
    if (pages.length > 1 && fac.length && handouts.length !== pages.length) printAll("pres.print_pages", pages);
    if (handouts.length > 1 || (handouts.length === 1 && pages.length > 1)) printAll("pres.print_handouts", handouts);
    heading(p, T("pres.tab_prepare"), tools.children.length ? tools : null);
    para(p, T("pres.prepare_intro"));
    if (!pages.length) { para(p, T("pres.prepare_none"), "gvp-pp gvp-pp--muted"); return; }
    pages.forEach(function (e) {
      var divider = e.slide.layout === "section";
      var card = el("section", "gvp-prep" + (divider ? " gvp-prep--part" : ""));
      card.appendChild(langOf(el("h5", "gvp-prep-h", titleOf(e)), e));
      var bs = el("p", "gvp-badges");
      if (e.slide.handout) bs.appendChild(badge(T("pres.b_handout")));
      if (e.slide.checklist) bs.appendChild(badge(T("pres.b_checklist")));
      if (!e.slide.facilitator && e.shown) bs.appendChild(badge(T("pres.b_in_show", { n: e.n })));
      if (bs.children.length) card.appendChild(bs);
      // a divider's notes are the section's own guidance ("Read these pages a week before …"): shown right here
      if (divider) card.appendChild(renderNotes(attrs(el("div", "gvp-prep-notes"), { lang: "en" }), e, P.cur, {}));
      if (e.slide.layout === "bullets" && e.slide.checklist) card.appendChild(checklist(e));
      var acts = el("div", "gvp-prep-acts");
      var view = btn("gvp-pill gvp-pill--sm", T("pres.view"), { icon: "eye" });
      view.addEventListener("click", function () { goToId(e.id, {}); });
      acts.appendChild(view);
      var pr = btn("gvp-pill gvp-pill--sm", T("pres.print_page"), { icon: "printer" });
      pr.addEventListener("click", function () { printDeck(P.deck.id, "pages", pr, [e.id]); });
      acts.appendChild(pr);
      card.appendChild(acts);
      p.appendChild(card);
    });
  }
  /** A checklist page with real tick boxes (kept on this device). */
  function checklist(e) {
    var ul = el("ul", "gvp-checks");
    var ticks = (ds().checks[e.id] || []).slice();
    var ctx = ctxFor(P.cur, "slide");
    function box(key, text, sub) {
      var li = el("li", sub ? "is-sub" : "");
      var lab = el("label", "gvp-check");
      var cb = el("input");
      cb.type = "checkbox";
      cb.checked = ticks.indexOf(key) >= 0;
      cb.addEventListener("change", function () {
        var list = ds().checks[e.id] || [];
        list = list.filter(function (x) { return x !== key; });
        if (cb.checked) list.push(key);
        if (list.length) ds().checks[e.id] = list; else delete ds().checks[e.id];
        touch(ds());
        saveState();
      });
      lab.appendChild(cb);
      var words = richInto(el("span", "gvp-check-t"), text, ctx);
      words.setAttribute("lang", e.slide.lang || "en");
      lab.appendChild(words);
      li.appendChild(lab);
      return li;
    }
    (e.slide.items || []).forEach(function (it, i) {
      if (it && typeof it === "object") {
        ul.appendChild(box(String(i), it.text || "", false));
        (it.items || []).forEach(function (x, j) { ul.appendChild(box(i + "." + j, x, true)); });
      } else ul.appendChild(box(String(i), it, false));
    });
    return ul;
  }

  /* ---------- Save & share ---------- */
  function panelSave(p) {
    heading(p, T("pres.tab_save"));
    var s1 = el("section", "gvp-sec");
    s1.appendChild(el("h5", "gvp-sec-h", T("pres.save_h")));
    s1.appendChild(el("p", "gvp-pp", T("pres.save_text")));
    var dl = btn("gvp-pill gvp-pill--primary", T("pres.save_btn"), { icon: "download" });
    dl.addEventListener("click", function () {
      flushEdits();
      var data = G.exportVersion(P.deck, STATE);
      var day = new Date().toISOString().slice(0, 10);
      download(P.deck.id + "-my-version-" + day + ".json", JSON.stringify(data, null, 2) + "\n");
      toast(T("pres.saved_file"));
    });
    s1.appendChild(dl);
    p.appendChild(s1);

    var s2 = el("section", "gvp-sec");
    s2.appendChild(el("h5", "gvp-sec-h", T("pres.open_h")));
    s2.appendChild(el("p", "gvp-pp", T("pres.open_text")));
    var file = el("input", "sr-only");
    file.type = "file";
    file.accept = ".json,application/json";
    file.id = newId("gvp-file");
    var lab = el("label", "gvp-pill gvp-filelabel");
    lab.htmlFor = file.id;
    lab.appendChild(icon("upload"));
    lab.appendChild(el("span", "", T("pres.open_btn")));
    var errs = el("div", "gvp-errors");
    errs.setAttribute("aria-live", "polite");
    file.addEventListener("change", function () {
      var f = file.files && file.files[0];
      file.value = "";
      clear(errs);
      if (!f) return;
      if (f.size > G.LIMITS.fileBytes) { showErrors(errs, [{ key: "pres.err.too_big", detail: "" }]); return; }
      var reader = new FileReader();
      reader.onload = function () { importText(String(reader.result || ""), errs); };
      reader.onerror = function () { showErrors(errs, [{ key: "pres.err.not_json", detail: "" }]); };
      reader.readAsText(f);
    });
    s2.appendChild(file);
    s2.appendChild(lab);
    s2.appendChild(errs);
    p.appendChild(s2);

    var s3 = el("section", "gvp-sec");
    s3.appendChild(el("h5", "gvp-sec-h", T("pres.print_h")));
    s3.appendChild(el("p", "gvp-pp", T("pres.print_text")));
    var row = el("div", "gvp-ph-tools gvp-ph-tools--wrap");
    G.PRINT_MODES.forEach(function (m) {
      var b = btn("gvp-pill gvp-pill--sm", T("pres.print_" + m), { icon: "printer" });
      // what each one prints, in the page's and the menus' words (title = the visible label + its description)
      b.title = T("pres.print_" + m + "_d");
      b.addEventListener("click", function () { printDeck(P.deck.id, m, b); });
      row.appendChild(b);
    });
    s3.appendChild(row);
    s3.appendChild(el("p", "gvp-pp gvp-pp--muted", T("pres.save_doc")));
    p.appendChild(s3);

    var s4 = el("section", "gvp-sec");
    s4.appendChild(el("h5", "gvp-sec-h", T("pres.reset_h")));
    s4.appendChild(el("p", "gvp-pp", T("pres.reset_text")));
    var rs = btn("gvp-pill", T("pres.reset_deck"), { icon: "rotate-ccw" });
    rs.disabled = !G.summary(ds(), P.deck).any;
    rs.addEventListener("click", function () {
      if (!window.confirm(T("pres.reset_confirm", { title: P.deck.title }))) return;
      flushEdits();
      var snap = snapshot();
      G.resetDeck(STATE, P.deck.id);
      changed();
      var b = toast(T("pres.reset_done", { title: P.deck.short || P.deck.title }), undoAction(snap));
      if (b) b.focus();
    });
    s4.appendChild(rs);
    // where "Reset all 4 to the original" is: the page shows it (under the presentations) when there is something
    // to reset in any of them
    if (anyState()) s4.appendChild(el("p", "gvp-pp gvp-pp--muted", T("pres.reset_all_note")));
    p.appendChild(s4);
    para(p, T("pres.privacy"), "gvp-pp gvp-pp--muted gvp-privacy");
  }
  function showErrors(box, errors) {
    clear(box);
    box.appendChild(el("p", "gvp-errors-h", T("pres.import_failed")));
    var ul = el("ul");
    errors.slice(0, 6).forEach(function (er) {
      ul.appendChild(el("li", "", T(er.key) + (er.detail ? " (" + er.detail + ")" : "")));
    });
    box.appendChild(ul);
  }
  function importText(text, errs) {
    var res = G.validateImport(text, P.deck);
    if (!res.ok) { showErrors(errs, res.errors); return; }
    if (!window.confirm(T("pres.import_confirm", { title: P.deck.title }))) return;
    var before = G.importVersion(STATE, P.deck, res.data);
    var id = P.deck.id;
    saveState();
    changed();
    var b = toast(T("pres.imported"), {
      label: T("pres.undo"),
      run: function () {
        if (before.deck) STATE.decks[id] = G.normDeck(before.deck); else delete STATE.decks[id];
        STATE.shared.fill = before.shared || {};
        saveState();
        if (P.root && P.deck && P.deck.id === id) changed();
        toast(T("pres.undone"));
      },
      after: function () { if (P.root) P.root.focus({ preventScroll: true }); },
    });
    if (b) b.focus();
  }
  function download(name, text) {
    var blob = new Blob([text], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var a = el("a");
    a.href = url;
    a.download = name;
    a.hidden = true;
    (P.root || document.body).appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(url); a.remove(); }, 1500);
  }

  /* ================================================================== 5. presenter view, two windows in step */
  var ME = Math.random().toString(36).slice(2);
  var CHANNEL = null;
  function channel() {
    if (CHANNEL !== null) return CHANNEL;
    try {
      CHANNEL = new BroadcastChannel("gv-presentations");
      CHANNEL.onmessage = function (m) { onSync(m.data); };
    } catch (e) { CHANNEL = false; }
    return CHANNEL;
  }
  function syncSend(msg) {
    if (!P.deck) return;
    msg.deck = P.deck.id;
    msg.from = ME;
    msg.at = Date.now();
    // which file of the deck this window has (the other one fetches a newer one rather than prune its own state)
    msg.built = P.deck.built || "";
    // a browser that keeps nothing: the other window cannot read the change back, so it travels with the message
    if (msg.kind === "state" && !storageOk) {
      msg.ds = G.deckState(STATE, P.deck.id);
      msg.shared = STATE.shared.fill;
    }
    var ch = channel();
    if (ch) {
      try { ch.postMessage(msg); } catch (e) { /* closed */ }
    } else {
      // no BroadcastChannel (an old Safari): the other window hears a storage event
      try { localStorage.setItem(SYNC_KEY, JSON.stringify(msg)); } catch (e) { /* no storage either */ }
    }
  }
  function syncHello() { syncSend({ kind: "hello" }); }
  function onSync(msg) {
    if (!msg || msg.from === ME || !P.root || !P.deck || msg.deck !== P.deck.id || !P.cur) return;
    if (typeof msg.built === "string" && Date.parse(msg.built) > Date.parse(P.deck.built || "")) refetchNewer(P.deck.id, msg.built);
    if (msg.kind === "go") {
      if (!P.cur.byId[msg.id]) { loadState(); refresh(); }
      goToId(msg.id, { silent: true });
    } else if (msg.kind === "black") setBlack(!!msg.on, true);
    else if (msg.kind === "state") {
      // the sender's version comes along only when it could not store it (blocked storage, a full one, an old
      // Safari's private window): this window cannot read it back either, even when its own reading works
      if (msg.ds) applyState(msg.ds, msg.shared);
      else reloadFromStorage();
    } else if (msg.kind === "hello") {
      var e = currentEntry();
      if (e && e.shown) syncSend({ kind: "go", id: e.id });
      if (!storageOk) syncSend({ kind: "state" });
    }
  }
  /** The other window's version of this deck, sent along because neither window can store it. */
  function applyState(raw, shared) {
    var norm = G.normState({ v: 1, shared: { fill: shared || {} }, decks: (function () { var d = {}; d[P.deck.id] = raw; return d; })() });
    STATE.decks[P.deck.id] = norm.decks[P.deck.id];
    STATE.shared.fill = norm.shared.fill;
    redrawAll();
  }
  /** Another window (or tab) changed the stored version: read it again and redraw — not the form being typed in.
   *  Never written back from here (prepare's save: false): that is what kept two windows rewriting it. */
  function reloadFromStorage() {
    loadState();
    renderStatuses();
    if (!P.root || !P.deck) return;
    prepare(P.deck, { save: false });
    redrawAll();
  }
  function redrawAll() {
    refresh();
    renderStage(0);
    renderChrome();
    renderNotesPanel();
    if (P.mode === "presenter") renderPresenter();
    var a = document.activeElement;
    var typing = a && a.closest && a.closest("[data-gvp-drawer]") && /^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName);
    if (P.drawer && !typing) renderPanel(P.tab);
  }
  window.addEventListener("storage", function (ev) {
    if (ev.key === SYNC_KEY && ev.newValue) {
      try { onSync(JSON.parse(ev.newValue)); } catch (e) { /* not ours */ }
      return;
    }
    if (ev.key === G.STORAGE_KEY || ev.key === null) reloadFromStorage();
  });

  /** "Presenter view": a second window with this slide, the next one, the notes in large type, a timer and the
   *  clock; this window stays the room's view. A blocked pop-up → presenter mode in this window. In the presenter
   *  window itself, the button goes back to the plain view. */
  function openPresenter() {
    if (!P.deck) return;
    closeMenu();
    if (P.mode === "presenter") { setMode("present"); return; }
    var e = currentEntry();
    var w = presenterWindow(P.deck.id, e && e.shown ? e.n : 1);
    if (!w) { popupNotice(); return; }
    try { w.focus(); } catch (err2) { /* fine */ }
    toast(T("pres.presenter_opened"));
  }
  /** The presenter's second window on slide n (one per deck: opening it again brings the same window back), or
   *  null when the browser stops it. Called right inside a click, which is what lets a pop-up through. */
  function presenterWindow(id, n) {
    var url = location.pathname + "?present=" + encodeURIComponent(id) + "&mode=presenter#slide-" + (n || 1);
    try { return window.open(url, "gvp-presenter-" + id, "popup,width=1280,height=820"); } catch (err) { return null; }
  }
  function setMode(mode) {
    P.mode = mode === "presenter" ? "presenter" : "present";
    P.root.setAttribute("data-mode", P.mode);
    var on = P.mode === "presenter";
    qa("[data-gvp-pv]").forEach(function (n) { n.hidden = !on; });
    pressed("presenter", on);
    if (on) {
      setNotes(true, true);
      startClock();
      renderPresenter();
    } else {
      stopClock();
      setNotes(VIEW.notes, true);
    }
    layoutStage();
    renderStage(0);
    renderChrome();
    setUrl();
    onResize();
  }
  function layoutNext() {
    var box = q("[data-gvp-pvnext-stage]");
    if (!box || box.offsetParent === null) return;
    var k = box.clientWidth / LOGICAL_W;
    if (k > 0) box.style.setProperty("--k", k.toFixed(5));
  }
  function renderPresenter() {
    if (P.mode !== "presenter" || !P.cur || !P.root) return;
    var e = currentEntry();
    var nxt = e && !P.preview ? P.cur.shown[P.i + 1] : null;
    var box = q("[data-gvp-pvnext-stage]");
    var label = q("[data-gvp-pvnext-label]");
    if (box) {
      clear(box);
      if (nxt) {
        var canvas = el("div", "gvp-canvas");
        var sl = renderSlide(nxt, P.cur, { variant: "thumb", n: nxt.n });
        canvas.appendChild(sl);
        box.appendChild(canvas);
        layoutNext();
        fitSlide(sl);
      }
    }
    if (label) {
      clear(label);
      if (nxt) tInto(label, "pres.next_slide", { n: nxt.n, title: titleOf(nxt) }, ["title"], nxt.slide.lang);
      else label.textContent = T("pres.next_end");
    }
    var plan = q("[data-gvp-pv-plan]");
    if (plan) plan.textContent = e && e.shown ? T("pres.plan", { at: G.clock(e.end), start: G.clock(e.start), about: G.aboutText(e.mins) }) : "";
    updateClock();
  }
  /* the timer (start / pause / reset) and the clock */
  var TIMER = { start: 0, acc: 0, running: false, tick: 0 };
  function elapsed() { return TIMER.acc + (TIMER.running ? Date.now() - TIMER.start : 0); }
  function startTimer() {
    if (TIMER.running) return;
    TIMER.running = true;
    TIMER.start = Date.now();
    updateClock();
    var p = q('[data-gvp-act="timer-pause"]');
    if (p && p.offsetParent) p.focus();
  }
  function pauseTimer() {
    if (!TIMER.running) return;
    TIMER.acc += Date.now() - TIMER.start;
    TIMER.running = false;
    updateClock();
    var s = q('[data-gvp-act="timer-start"]');
    if (s && s.offsetParent) s.focus();
  }
  function stopTimer(quiet) {
    TIMER.running = false;
    TIMER.acc = 0;
    TIMER.start = 0;
    if (!quiet) updateClock();
  }
  function startClock() {
    clearInterval(TIMER.tick);
    TIMER.tick = setInterval(updateClock, 1000);
  }
  function stopClock() { clearInterval(TIMER.tick); TIMER.tick = 0; }
  function hms(sec) {
    var h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
    return (h ? h + ":" + (m < 10 ? "0" : "") : "") + m + ":" + (s < 10 ? "0" : "") + s;
  }
  function updateClock() {
    if (!P.root) { stopClock(); return; }
    var t = q("[data-gvp-pv-timer]");
    if (!t) return;
    var ms = elapsed();
    t.textContent = hms(Math.floor(ms / 1000));
    var clock = q("[data-gvp-pv-clock]");
    if (clock) {
      try { clock.textContent = new Date().toLocaleTimeString(LANG === "es" ? "es-US" : "en-US", { hour: "numeric", minute: "2-digit" }); } catch (e) { clock.textContent = ""; }
    }
    var st = q('[data-gvp-act="timer-start"]'), pa = q('[data-gvp-act="timer-pause"]');
    if (st) st.hidden = TIMER.running;
    if (pa) pa.hidden = !TIMER.running;
    var pace = q("[data-gvp-pv-pace]");
    var e = currentEntry();
    if (pace) {
      var txt = "", cls = "";
      if (e && e.shown && ms > 0) {
        var m = ms / 60000;
        if (m > e.end + 0.5) { txt = T("pres.pace_behind", { n: Math.max(1, Math.round(m - e.end)) }); cls = "is-behind"; }
        else if (m < e.start - 0.5) { txt = T("pres.pace_ahead", { n: Math.max(1, Math.round(e.start - m)) }); cls = "is-ahead"; }
        else { txt = T("pres.pace_on_time"); cls = "is-on"; }
      }
      pace.textContent = txt;
      pace.className = "gvp-pv-pace " + cls;
    }
  }

  /* ================================================================== 6. print
     Four ways, each the presenter's CURRENT version (their version, details and edits): slides (one slide per
     page, landscape) · notes (each slide with its speaker notes and TIME line) · handout (three slides per page
     with lines for notes, for the participants) · script (the notes only, under each slide's title) — and "pages"
     (Prepare: the facilitator's pages and the participants' handouts, landscape unless a page says `print:
     "portrait"`). Built into #gvp-print — real headings, lists and paragraphs in English (lang="en"), so the
     document the print window saves is a tagged one; html.gvp-printing hides everything else while the print
     window is open (also the GVR / RLV 101 handout the page prints by itself). The print window can also save it
     as a document: its name is then the deck, the mode and the day. */
  var PRINT = { busy: false, active: false, title: null };
  /** The slides' fonts loaded (the text is fitted with them) — but never a print that waits for ever: after 2.5 s
   *  it goes on with what there is. */
  function fontsReady() {
    if (!document.fonts || !document.fonts.load) return Promise.resolve();
    var loads = ['400 32px "Inter Variable"', '700 32px "Inter Variable"', 'italic 400 32px "Inter Variable"', '500 48px "Fraunces Variable"', 'italic 400 40px "Fraunces Variable"'];
    var all = Promise.all(loads.map(function (f) { return document.fonts.load(f).catch(function () {}); }));
    var cap = new Promise(function (resolve) { setTimeout(resolve, 2500); });
    return Promise.race([all, cap]).then(function () {}, function () {});
  }
  function cssString(s) { return '"' + String(s || "").replace(/[\\"]/g, "\\$&").replace(/[\r\n]+/g, " ") + '"'; }
  function pageCss(title) {
    var foot = "@bottom-left { content: " + cssString(title) + "; font: 8pt/1.2 \"Inter Variable\", Arial, sans-serif; color: #555; }"
      + " @bottom-right { content: counter(page); font: 8pt/1.2 \"Inter Variable\", Arial, sans-serif; color: #555; }";
    return "@page gvp-land { size: landscape; margin: 0.4in 0.45in 0.5in; " + foot + " }\n"
      + "@page gvp-port { size: portrait; margin: 0.55in 0.6in 0.6in; " + foot + " }\n";
  }
  function slideBox(e, cur, cls) {
    var box = el("div", cls);
    var canvas = el("div", "gvp-canvas");
    canvas.appendChild(renderSlide(e, cur, { variant: "print", n: e.shown ? e.n : null }));
    box.appendChild(canvas);
    return box;
  }
  function printHead(cur, text) {
    var h = el("p", "gvp-pp-head");
    h.appendChild(el("span", "", cur.deck.title));
    h.appendChild(el("span", "", text));
    return h;
  }
  function buildPrint(cur, mode, ids) {
    cleanupPrint();
    var root = el("div", "gvp-print gvp-print--" + mode);
    root.id = "gvp-print";
    // not hidden from assistive technology: off the screen it is visibility:hidden (nothing to hear), and the
    // print window builds the saved document's headings, lists and paragraphs from it
    root.setAttribute("lang", "en");
    var style = el("style");
    style.id = "gvp-print-style";
    style.textContent = pageCss(cur.deck.title);
    document.head.appendChild(style);
    var N = cur.shown.length;
    var preset = cur.preset && cur.preset.label ? cur.preset.label.en || "" : "";
    if (mode === "slides") {
      cur.shown.forEach(function (e) {
        var pg = el("div", "gvp-pp gvp-pp--slide");
        pg.appendChild(slideBox(e, cur, "gvp-pp-slide"));
        root.appendChild(pg);
      });
    } else if (mode === "notes") {
      cur.shown.forEach(function (e) {
        var pg = el("div", "gvp-pp gvp-pp--notes");
        pg.appendChild(printHead(cur, G.fmt("Slide {n} of {total}", { n: e.n, total: N })));
        pg.appendChild(slideBox(e, cur, "gvp-pp-slide"));
        var notes = el("div", "gvp-pp-notes");
        notes.setAttribute("lang", "en");
        renderNotes(notes, e, cur, {});
        pg.appendChild(notes);
        root.appendChild(pg);
      });
    } else if (mode === "handout") {
      // three slides a page, each beside ruled lines that fill its third of the sheet (PowerPoint's 3-slide handout)
      var pages = Math.ceil(N / 3);
      for (var pgi = 0; pgi < pages; pgi++) {
        var pg2 = el("div", "gvp-pp gvp-pp--handout");
        pg2.appendChild(printHead(cur, G.fmt("Page {n} of {total}", { n: pgi + 1, total: pages })));
        cur.shown.slice(pgi * 3, pgi * 3 + 3).forEach(function (e) {
          var row = el("div", "gvp-ho-row");
          row.appendChild(slideBox(e, cur, "gvp-ho-slide"));
          row.appendChild(attrs(el("div", "gvp-ho-lines"), { "aria-hidden": "true" }));
          pg2.appendChild(row);
        });
        root.appendChild(pg2);
      }
    } else if (mode === "script") {
      var head = el("div", "gvp-sc-head");
      head.appendChild(el("h1", "", cur.deck.title));
      // the length once: a version label that gives it ("Full workshop (about 90 minutes)") is followed by the slide
      // count only, never by a second, computed length that can differ by a minute or two
      var lenInLabel = /\(about [^)]*\)/i.test(preset || "");
      head.appendChild(el("p", "", "Speaker script · " + [preset, lenInLabel ? G.fmt("{n} slides", { n: N })
        : G.fmt("{n} slides, about {min} minutes", { n: N, min: Math.max(1, Math.round(cur.total)) })].filter(Boolean).join(" · ")));
      root.appendChild(head);
      cur.shown.forEach(function (e) {
        var item = el("section", "gvp-sc-item");
        var h = el("h2", "", e.n + ". ");
        richInto(h, e.slide.title, ctxFor(cur, "slide"));
        item.appendChild(h);
        var notes = el("div", "gvp-pp-notes");
        notes.setAttribute("lang", "en");
        renderNotes(notes, e, cur, {});
        item.appendChild(notes);
        root.appendChild(item);
      });
    } else if (mode === "pages") {
      (ids || []).forEach(function (id) {
        var e = cur.byId[id];
        if (!e) return;
        // the deck's handouts were landscape slides: a page prints landscape unless it says `print: "portrait"`
        var pg3 = el("div", "gvp-pp gvp-pp--page " + (e.slide.print === "portrait" ? "is-port" : "is-land") + (e.slide.handout ? " is-handout" : ""));
        pg3.appendChild(renderSlide(e, cur, { variant: "page" }));
        // a page for the facilitator keeps its notes (the instructions); a handout for the room never has any
        if (e.slide.facilitator && !e.slide.handout && G.noteLines(e.slide.notes, cur.preset && cur.preset.id).length) {
          var pn = el("div", "gvp-pp-notes gvp-pp-notes--page");
          renderNotes(pn, e, cur, {});
          pg3.appendChild(pn);
        }
        root.appendChild(pg3);
      });
    }
    document.body.appendChild(root);
    // the slides fitted at their own size while the container is laid out (off the screen) before printing — on
    // paper nothing scrolls, so an overlong slide shrinks further than on a screen rather than lose its end
    Array.prototype.forEach.call(root.querySelectorAll(".gvp-canvas > .gvp-slide"), function (sl) { fitSlide(sl, PRINT_FLOOR); });
    document.documentElement.setAttribute("data-gvp-print", mode);
    return root;
  }
  function cleanupPrint() {
    var old = document.getElementById("gvp-print");
    if (old) old.remove();
    var st = document.getElementById("gvp-print-style");
    if (st) st.remove();
    document.documentElement.classList.remove("gvp-printing");
    document.documentElement.removeAttribute("data-gvp-print");
    if (PRINT.title !== null) { document.title = PRINT.title; PRINT.title = null; }
    PRINT.active = false;
  }
  /** The page's title while the print window is open — the name it gives a copy saved as a document:
   *  "Information Workshop – Handout for participants – 2026-10-02". */
  function printTitle(cur, mode, ids) {
    var what = T("pres.print_" + mode);
    if (mode === "pages") {
      var list = (ids || []).map(function (id) { return cur.byId[id]; }).filter(Boolean);
      what = list.length === 1 ? titleIn(list[0], cur) : list.every(function (e) { return e.slide.handout; }) ? T("pres.print_handout") : T("pres.print_pages_file");
    }
    var d = new Date();
    var day = d.getFullYear() + "-" + (d.getMonth() < 9 ? "0" : "") + (d.getMonth() + 1) + "-" + (d.getDate() < 10 ? "0" : "") + d.getDate();
    if (PRINT.title === null) PRINT.title = document.title;
    document.title = [cur.deck.short || cur.deck.title, what, day].join(" – ");
  }
  function titleIn(e, cur) { return plainText(e.slide.title, ctxFor(cur, "slide")); }
  /** Prints deck `id` in `mode` (from the page or from the player); `ids`: the pages for "pages". */
  function printDeck(id, mode, src, ids) {
    if (PRINT.busy) return;
    if (G.PRINT_MODES.indexOf(mode) < 0 && mode !== "pages") mode = "slides";
    PRINT.busy = true;
    if (src) src.setAttribute("aria-busy", "true");
    // a word when it takes a moment (the deck's file or the slides' fonts on a slow connection): the click shows
    var said = null;
    var wait = setTimeout(function () { toast(T("pres.print_wait")); said = TOAST.el; }, 300);
    var quiet = function () { clearTimeout(wait); if (said && TOAST.el === said) hideToast(said, false); };
    var done = function () { quiet(); PRINT.busy = false; if (src) src.removeAttribute("aria-busy"); };
    // from the page: the stored version as it is now; with the player open, its state is the current one (and
    // must stay the same object: Customize holds it)
    if (!P.root) loadState();
    fetchDeck(id).then(function (deck) {
      prepare(deck);
      return fontsReady().then(function () { return deck; });
    }).then(function (deck) {
      var cur = G.current(deck, STATE, "", Date.now());
      buildPrint(cur, mode, ids);
      quiet();
      PRINT.active = true;
      document.documentElement.classList.add("gvp-printing");
      printTitle(cur, mode, ids);
      // a moment for the layout before the print window takes its snapshot. The print window holds this page
      // until it closes: only then is a click that came in meanwhile (a double click, a tap during the build) free
      // to start another print — not a second print window right after the first
      setTimeout(function () {
        try { window.print(); } catch (e) { cleanupPrint(); } finally { setTimeout(done, 400); }
      }, 60);
    }, function () {
      done();
      toast(T("pres.load_failed"));
    });
  }
  window.addEventListener("beforeprint", function () {
    if (PRINT.active) return;
    // the browser's own Print while the player is open: the slides of the version on the stage
    if (P.root && P.cur) {
      buildPrint(P.cur, "slides");
      PRINT.active = true;
      document.documentElement.classList.add("gvp-printing");
      printTitle(P.cur, "slides");
    }
  });
  window.addEventListener("afterprint", function () { setTimeout(cleanupPrint, 0); });

  /* ================================================================== 7. the page: cards, statuses, reset */
  function presetLabel(meta, id) {
    var p = (meta.presets || []).filter(function (x) { return x.id === id; })[0];
    return p ? (p.label && (p.label[LANG] || p.label.en)) || id : id;
  }
  function anyState() {
    if (G.sharedCount(STATE)) return true;
    return Object.keys(STATE.decks).some(function (id) { return G.summary(STATE.decks[id], META[id]).any; });
  }
  /** [data-pres-status="<id>"]: what this device changed, and the last slide shown (with "Resume"). */
  function renderStatuses() {
    Array.prototype.forEach.call(document.querySelectorAll("[data-pres-status]"), function (node) {
      var id = node.getAttribute("data-pres-status");
      var meta = META[id] || {};
      var sum = G.summary(STATE.decks[id], meta);
      var parts = [];
      if (sum.preset) parts.push(T("pres.st_version", { label: presetLabel(meta, sum.preset) }));
      if (sum.hidden) parts.push(TN("pres.st_hidden", sum.hidden));
      if (sum.shown) parts.push(TN("pres.st_shown", sum.shown));
      if (sum.edited) parts.push(TN("pres.st_edited", sum.edited));
      if (sum.added) parts.push(TN("pres.st_added", sum.added));
      if (sum.moved) parts.push(T("pres.st_moved"));
      if (sum.details) parts.push(TN("pres.st_details", sum.details));
      clear(node);
      // a browser that keeps nothing: the changes are only for this visit, not "on this device"
      if (parts.length) node.appendChild(el("span", "gvp-st-changed", T(storageOk ? "pres.st_changed" : "pres.st_changed_visit", { list: parts.join(", ") })));
      // (slide 1: opened and closed again — "Resume" would do what Present does)
      if (sum.last > 1) {
        if (parts.length) node.appendChild(document.createTextNode(" · "));
        node.appendChild(el("span", "gvp-st-last", sum.last_of ? T("pres.st_last", { n: sum.last, total: sum.last_of }) : T("pres.st_last_n", { n: sum.last })));
        node.appendChild(document.createTextNode(" · "));
        var a = el("a", "gvp-st-resume", T("pres.st_resume"));
        a.href = "?present=" + encodeURIComponent(id) + "#slide-" + sum.last;
        a.setAttribute("data-pres-open", id);
        a.setAttribute("data-pres-slide", String(sum.last));
        a.setAttribute("aria-label", T("pres.st_resume_label", { n: sum.last, title: meta.short || meta.title || id }));
        node.appendChild(a);
      }
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-pres-reset]"), function (b) {
      var id = b.getAttribute("data-pres-reset");
      b.hidden = id === "all" ? !anyState() : !G.summary(STATE.decks[id], META[id]).any;
    });
  }
  function fieldValue(form, name) {
    var els = form.querySelectorAll('[name="' + name + '"]');
    for (var i = 0; i < els.length; i++) {
      var x = els[i];
      if (x.type === "radio" || x.type === "checkbox") { if (x.checked) return x.value; }
      else if (x.value) return x.value;
    }
    return "";
  }
  function printFromHook(b) {
    var id = b.getAttribute("data-pres-print") || "";
    var mode = b.getAttribute("data-pres-print-mode") || "";
    var form = b.closest("form, [data-pres-print-form]");
    if (form) {
      if (!id) id = fieldValue(form, "deck");
      if (!mode) mode = fieldValue(form, "mode");
    }
    if (!id || !G.ID.test(id)) return;
    printDeck(id, mode || "slides", b);
  }
  /** A[data-pres-open] clicked: the player opens on this page (the link's own address is for a new tab). A card's
   *  "Presenter view" opens the presenter's window now, in this click (a pop-up needs one), and this window becomes
   *  the room's view; a pop-up the browser stopped is said in the player, with presenter mode in here instead. */
  function openFromLink(e, open) {
    if (e.gvpDone) return;                                                     // (seen by the link's own listener)
    if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;   // a new tab: let it load
    if (!document.getElementById("gvp-tpl")) return;
    e.gvpDone = true;
    e.preventDefault();
    var id = open.getAttribute("data-pres-open");
    var mode = open.getAttribute("data-pres-mode") || "present";
    var slide = Number(open.getAttribute("data-pres-slide")) || 0;
    var blocked = false;
    if (mode === "presenter" && G.ID.test(id)) {
      blocked = !presenterWindow(id, slide || 1);
      mode = "present";
    }
    openPlayer(id, { mode: mode, opener: open, slide: slide, popupBlocked: blocked });
  }
  // The presenter links get a listener of their own: Edge (and Chrome) let a click open a pop-up window from a
  // listener on the link or an element around it — not from one on the document, the body or the window (the
  // window is then never made, though window.open answers as if it were).
  function bindPresenterLinks() {
    Array.prototype.forEach.call(document.querySelectorAll('[data-pres-open][data-pres-mode="presenter"]'), function (a) {
      if (a.getAttribute("data-gvp-bound")) return;
      a.setAttribute("data-gvp-bound", "");
      a.addEventListener("click", function (e) { openFromLink(e, a); });
    });
  }
  function focusAfterReset(id) {
    var to = id && id !== "all" ? document.querySelector('[data-pres-open="' + id + '"]') : document.querySelector("[data-pres-open]");
    if (to && to.focus) to.focus({ preventScroll: true });
  }
  function resetFromPage(b) {
    var id = b.getAttribute("data-pres-reset");
    loadState();
    if (id === "all") {
      if (!window.confirm(T("pres.reset_all_confirm"))) return;
      var before = G.resetAll(STATE);
      saveState();
      var u = toast(T("pres.reset_all_done"), {
        label: T("pres.undo"),
        run: function () { STATE = G.normState(before); saveState(); toast(T("pres.undone")); focusAfterReset("all"); },
        after: function () { focusAfterReset("all"); },
      });
      if (u) u.focus();
      return;
    }
    var meta = META[id] || {};
    var title = meta.short || meta.title || id;
    if (!window.confirm(T("pres.reset_confirm", { title: meta.title || title }))) return;
    var snap = G.resetDeck(STATE, id);
    saveState();
    var u2 = toast(T("pres.reset_done", { title: title }), {
      label: T("pres.undo"),
      run: function () { G.restoreDeck(STATE, id, snap); saveState(); toast(T("pres.undone")); focusAfterReset(id); },
      after: function () { focusAfterReset(id); },
    });
    if (u2) u2.focus();
  }
  document.addEventListener("click", function (e) {
    var t = e.target;
    if (!t || !t.closest) return;
    var open = t.closest("[data-pres-open]");
    if (open && !(P.root && P.root.contains(open))) {
      openFromLink(e, open);
      return;
    }
    var pr = t.closest("[data-pres-print]");
    if (pr && !(P.root && P.root.contains(pr))) {
      e.preventDefault();
      printFromHook(pr);
      return;
    }
    var rs = t.closest("[data-pres-reset]");
    if (rs) { e.preventDefault(); resetFromPage(rs); }
  });
  // a print form submitted with Enter (the "Print or save a copy" card)
  document.addEventListener("submit", function (e) {
    var f = e.target && e.target.closest ? e.target.closest("[data-pres-print-form]") : null;
    if (!f) return;
    e.preventDefault();
    var b = (e.submitter && e.submitter.hasAttribute("data-pres-print")) ? e.submitter : f.querySelector("[data-pres-print]") || f;
    if (b === f) {
      var id = fieldValue(f, "deck");
      if (id && G.ID.test(id)) printDeck(id, fieldValue(f, "mode") || "slides", null);
    } else printFromHook(b);
  });

  // A deck's file (and the slides' fonts) fetched as the pointer or the focus reaches its Present or Print: the
  // click then prints or opens without the wait.
  function prefetch(e) {
    var t = e.target;
    var hook = t && t.closest ? t.closest("[data-pres-print], [data-pres-open]") : null;
    if (!hook || (P.root && P.root.contains(hook))) return;
    var id = hook.getAttribute("data-pres-open") || hook.getAttribute("data-pres-print") || "";
    var form = hook.closest("form, [data-pres-print-form]");
    if (form && hook.hasAttribute("data-pres-print")) id = fieldValue(form, "deck") || id;
    if (!G.ID.test(id) || DECKS[id] || PENDING[id]) return;
    fetchDeck(id).catch(function () { /* the click tries again */ });
    if (hook.hasAttribute("data-pres-print")) fontsReady();
  }
  document.addEventListener("pointerover", prefetch);
  document.addEventListener("focusin", prefetch);

  function startPage() {
    loadState();
    renderStatuses();
    bindPresenterLinks();
    // the page's live region (Reset … Undo, "Preparing the print…"), there before it has anything to say
    if (document.querySelector("[data-pres-reset], [data-pres-print], [data-pres-open]")) pageToast();
    var id = "", mode = "";
    try {
      var sp = new URLSearchParams(location.search);
      id = sp.get("present") || "";
      mode = sp.get("mode") || "";
    } catch (e) { id = ""; }
    if (id && G.ID.test(id) && document.getElementById("gvp-tpl")) {
      openPlayer(id, { mode: ["present", "customize", "presenter", "overview"].indexOf(mode) >= 0 ? mode : "present", slide: slideFromHash(location.hash) });
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", startPage);
  else startPage();
})();
