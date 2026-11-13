/* NETA 65 Grapevine / La Viña — Published Writers page: the Texas writers archive (#archive on
   /published/ and /es/published/).
   ------------------------------------------------------------------
   src/pages/published.njk renders the archive's Area 65 stories as rows (li.pw-arc-row: data-scope,
   data-pub, data-dec = decade "1990" | "undated", data-y = year, data-o = place in the whole list,
   data-s = search words), grouped by decade, newest first; without JavaScript all of them show. The
   rest of Texas is in /published/texas-archive.json (src/pages/published-archive-json.11ty.js), fetched
   once — the first time the page's scope asks for it. This script (loaded after published.js):
     - follows the page's filter card (published.js: window.GVPW.state, then a "pw:state" event on
       document after each change): where the writers are from (Area 65 → the Area 65 rows; All of
       Texas / Everyone → every row, Area 65 marked), magazine, and the search (the cards' rule: every
       word must start a word of data-s — "dal" finds Dallas; a year is a whole word: "1990" finds
       1990, not the whole decade "1990s")
     - adds the decade: ?dec=1990s | undated in the address, next to the page's own keys ("pw:reset",
       the filter card's Reset, clears it; written again after Back / Forward)
     - live counts on the decade and hometown chips, a live result line, empty decades hidden
     - 40 rows, then "Show 40 more" / "Show all N"; keyboard focus moves to the first row that appears
     - the hometown chips put the name into the page's search box (one search for the whole page)
     - builds the rows of the JSON with textContent only, and links only to the magazines' own pages
     - the note over the list ("Titles translated automatically …") while a row with a machine
       translation (data-mt) is shown
   Strings and settings come from <script id="pw-arc-config"> (eleventy/filters/published.js → pwArchive;
   its json address ends in ?v=<the file's fingerprint>). */
(function () {
  "use strict";
  var cfgEl = document.getElementById("pw-arc-config");
  var root = document.getElementById("pw-arc");
  var list = document.getElementById("pw-arc-list");
  if (!cfgEl || !root || !list) return;
  var C;
  try { C = JSON.parse(cfgEl.textContent); } catch (e) { return; }
  var S = C.s || {};
  var PAGE = Number(C.page) || 40;
  var SCOPES = { neta65: 1, texas: 1, all: 1 };
  var PUBS = { all: 1, gv: 1, lv: 1 };
  // the only links a row may have (eleventy/filters/published.js ARC_URL)
  var SAFE_URL = /^https:\/\/(?:www\.)?(?:aagrapevine|aalavina)\.org\/\S*$/;
  var FETCH_TIMEOUT = 20000;
  var $ = function (id) { return document.getElementById(id); };
  var form = $("pw-form"), qInput = $("pw-q");
  var statusEl = $("pw-arc-status"), note = $("pw-arc-note"), emptyEl = $("pw-arc-empty"), mtNote = $("pw-arc-mt");
  var retryBtn = root.querySelector("[data-arc-retry]");
  var more = $("pw-arc-more"), shownNote = $("pw-arc-shown");
  var pageBtn = root.querySelector('[data-arc-more="page"]'), allBtn = root.querySelector('[data-arc-more="all"]');
  var decRadios = root.querySelectorAll('input[name="pw-dec"]');
  var places = root.querySelectorAll("[data-arc-place]");

  var numFmt = null;
  try { numFmt = new Intl.NumberFormat(C.lang === "es" ? "es-US" : "en-US"); } catch (e) {}
  function num(n) { return numFmt ? numFmt.format(n) : String(n); }
  function fill(tpl, vars) {
    return String(tpl || "").replace(/\{(\w+)\}/g, function (m, k) { return vars[k] !== undefined && vars[k] !== null ? String(vars[k]) : m; });
  }
  function stories(n) { return fill(n === 1 ? S["n_stories.one"] : S["n_stories.other"], { n: num(n) }); }

  /* Same normalization as pwNorm() in eleventy/filters/published.js and norm() in published.js */
  var NON_WORD;
  try { NON_WORD = new RegExp("[^\\p{L}\\p{N}]+", "gu"); } catch (e) { NON_WORD = /[^a-z0-9\u00c0-\u024f]+/g; }
  var INITIALS = null;   // "H. T. B." → "HTB" (the edge before them is a group: no lookbehind, for Safari before 16.4)
  try { INITIALS = new RegExp("(^|[^\\p{L}\\p{N}])(\\p{L}\\.(?:\\s*\\p{L}\\.)+)", "gu"); } catch (e) {}
  function norm(s) {
    var t = String(s || "");
    if (INITIALS) t = t.replace(INITIALS, function (m, pre, ini) { return pre + ini.replace(/[.\s]/g, ""); });
    t = t.toLowerCase();
    if (t.normalize) t = t.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    return t.replace(/['\u2018\u2019\u02bc]/g, "").replace(NON_WORD, " ").trim();   // "Beginner's" → "beginners"
  }
  function tokens(q) { return norm(q).split(" ").filter(Boolean); }

  /* ---------- the decade groups and their rows (in page order) ---------- */
  var groups = [];
  Array.prototype.forEach.call(list.querySelectorAll(".pw-arc-dec"), function (el) {
    groups.push({ key: el.getAttribute("data-dec"), el: el, n: el.querySelector("[data-arc-n]"), ol: el.querySelector("ol"), rows: [] });
  });
  var rows = [];
  function collect() {
    rows = [];
    groups.forEach(function (g) {
      g.rows = [];
      if (!g.ol) return;
      Array.prototype.forEach.call(g.ol.children, function (li) {
        if (!li.classList.contains("pw-arc-row")) return;
        var r = { el: li, scope: li.getAttribute("data-scope"), pub: li.getAttribute("data-pub"), dec: li.getAttribute("data-dec"),
                  s: " " + (li.getAttribute("data-s") || "") + " ", mt: li.hasAttribute("data-mt") };
        g.rows.push(r);
        rows.push(r);
      });
    });
  }
  collect();
  var DECS = {};
  Array.prototype.forEach.call(decRadios, function (r) { DECS[r.value] = 1; });

  /* ---------- state: the page's choices (published.js) + the decade ---------- */
  var st = { scope: "neta65", pub: "all", q: "", dec: "all" };
  function fromPage(s) {
    if (!s) return;
    if (SCOPES[s.scope]) st.scope = s.scope;
    if (PUBS[s.pub]) st.pub = s.pub;
    st.q = String(s.q || "").slice(0, 100);
  }
  fromPage(window.GVPW && window.GVPW.state);
  var showN = PAGE;          // rows shown (across the decades) until "Show 40 more" / "Show all"

  function match(r, s, toks) {
    if (s.scope === "neta65" && r.scope !== "neta65") return false;
    if (s.pub !== "all" && r.pub !== s.pub) return false;
    if (s.dec !== "all" && r.dec !== s.dec) return false;
    for (var i = 0; i < toks.length; i++) {
      // every word must appear, at the start of a word — a year (4 digits) as a whole word: "1990" is not "1990s"
      var t = toks[i], w = /^\d{4}$/.test(t) ? " " + t + " " : " " + t;
      if (r.s.indexOf(w) === -1) return false;
    }
    return true;
  }
  function count(over) {
    var s = { scope: st.scope, pub: st.pub, q: st.q, dec: st.dec };
    for (var k in over) s[k] = over[k];
    var toks = tokens(s.q), n = 0;
    for (var i = 0; i < rows.length; i++) if (match(rows[i], s, toks)) n++;
    return n;
  }

  /* ---------- URL: ?dec=1990s | undated (the page's own keys and the #hash are kept) ---------- */
  function readUrl() {
    var p;
    try { p = new URLSearchParams(location.search); } catch (e) { return; }
    var d = String(p.get("dec") || "").toLowerCase().replace(/^(\d{4})s$/, "$1");
    if (DECS[d]) st.dec = d;
  }
  function writeUrl() {
    if (!window.history || !history.replaceState) return;
    var p;
    try { p = new URLSearchParams(location.search); } catch (e) { return; }
    if (st.dec !== "all") p.set("dec", st.dec === "undated" ? "undated" : st.dec + "s"); else p.delete("dec");
    var qs = p.toString();
    try { history.replaceState(history.state, "", location.pathname + (qs ? "?" + qs : "") + location.hash); } catch (e) {}
  }

  /* ---------- the rest of Texas (JSON), fetched once when the scope asks for it ---------- */
  var loaded = !Number(C.rest), loading = false, failed = false;
  function needRest() { return st.scope !== "neta65"; }
  function load() {
    if (loaded || loading) return;
    if (!window.fetch) { failed = true; return; }
    loading = true;
    failed = false;
    var ctrl = null, timer = 0;
    try { ctrl = new AbortController(); timer = setTimeout(function () { ctrl.abort(); }, FETCH_TIMEOUT); } catch (e) { ctrl = null; }
    var url = window.GV && window.GV.url ? window.GV.url(C.json) : C.json;
    fetch(url, ctrl ? { credentials: "same-origin", signal: ctrl.signal } : { credentials: "same-origin" })
      .then(function (res) { if (!res.ok) throw new Error("HTTP " + res.status); return res.json(); })
      .then(function (data) {
        clearTimeout(timer);
        insert(data && Array.isArray(data.items) ? data.items : []);
        loading = false;
        loaded = true;
        render({ keepUrl: true });
      })
      .catch(function () {
        clearTimeout(timer);
        loading = false;
        failed = true;
        render({ keepUrl: true });
      });
  }

  var SVG = "http://www.w3.org/2000/svg";
  function icon(name, cls) {
    var svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("class", "icon " + cls);
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    var use = document.createElementNS(SVG, "use");
    use.setAttribute("href", "#pw-i-" + name);   // the page's icon sprite (published.njk CARD_ICONS)
    svg.appendChild(use);
    return svg;
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = String(text);
    return e;
  }
  function langOf(v) { return v === "en" || v === "es" ? v : ""; }
  function hostOf(u) { var m = /^https:\/\/(?:www\.)?([^\/]+)/.exec(u); return m ? m[1] : ""; }
  function flag(name, text) { var f = el("span", "pw-arc-flag"); f.appendChild(icon(name, "size-3")); f.appendChild(document.createTextNode(text || "")); return f; }

  /* One row of the JSON → the same markup as the page's rows (published.njk arcRow). */
  function buildRow(x) {
    if (!x || typeof x !== "object" || !x.t) return null;
    var u = String(x.u || "");
    if (!SAFE_URL.test(u)) return null;
    var pub = x.p === "lv" ? "lv" : "gv";
    var li = el("li", "pw-arc-row");
    li.setAttribute("data-scope", "texas");
    li.setAttribute("data-pub", pub);
    li.setAttribute("data-dec", /^\d{4}$/.test(String(x.d)) ? String(x.d) : "undated");
    li.setAttribute("data-y", /^\d{4}$/.test(String(x.y)) ? String(x.y) : "");
    li.setAttribute("data-o", String(Number(x.o) || 0));
    li.setAttribute("data-s", norm(x.s));
    if (x.m || x.rm) li.setAttribute("data-mt", "");
    var tile = el("span", "pw-arc-tile");
    tile.setAttribute("data-pub", pub);
    tile.setAttribute("aria-hidden", "true");
    tile.appendChild(icon("grapes", "size-4"));
    var body = el("div", "pw-arc-body");

    var a = el("a", "pw-arc-link");
    a.href = u;
    a.target = "_blank";
    a.rel = "noopener";
    if (langOf(x.tl)) { var ts = el("span", "", x.t); ts.lang = x.tl; a.appendChild(ts); }
    else a.appendChild(document.createTextNode(String(x.t)));
    if (x.m) a.appendChild(el("span", "sr-only", " (" + (S["common.auto_translated"] || "") + ")"));   // the title is the machine translation
    a.appendChild(el("span", "sr-only", " " + fill(S.opens_on, { host: hostOf(u) })));
    var tp = el("p", "pw-arc-title");
    tp.appendChild(a);
    body.appendChild(tp);
    if (x.g) {
      var op = el("p", "pw-arc-orig");
      if (x.m) op.appendChild(icon("languages", "size-3"));
      op.appendChild(el("span", "sr-only", (S.original_title || "") + ": "));
      var os = el("span", "", x.g);
      if (langOf(x.gl)) os.lang = x.gl;
      op.appendChild(os);
      body.appendChild(op);
    }
    if (Array.isArray(x.b) && x.b.length) {
      var by = el("p", "pw-arc-by meta-row");
      if (x.w) by.setAttribute("data-w", "");
      x.b.forEach(function (part, i) {
        var item = el("span");
        if (i === 0) item.appendChild(el("span", "sr-only", (x.w ? S["archive.writers"] : S.writer) + ": "));
        item.appendChild(document.createTextNode(String(part)));
        by.appendChild(item);
      });
      if (x.c) by.appendChild(el("span", "pw-county", x.c));
      body.appendChild(by);
    }
    var meta = el("p", "pw-arc-meta meta-row");
    meta.appendChild(el("span", "pw-arc-pub", (C.pubs || {})[pub] || pub));
    if (x.i) meta.appendChild(el("span", "", x.i));
    if (x.h) { var th = el("span", "pw-arc-theme", x.h); if (langOf(x.hl)) th.lang = x.hl; meta.appendChild(th); }
    if (x.a) meta.appendChild(flag("headphones", S["archive.audio"]));
    if (x.x) meta.appendChild(flag("sparkles", S.online_exclusive));
    if (x.k) meta.appendChild(flag("mail", S["archive.column"]));
    body.appendChild(meta);
    if (x.r) {
      var br = el("p", "pw-arc-brief");
      if (langOf(x.rl)) br.lang = x.rl;
      if (x.rm) {   // a machine-translated subtitle under a title without the mark
        br.appendChild(icon("languages", "size-3"));
        br.appendChild(el("span", "sr-only", (S["common.auto_translated"] || "") + ": "));
      }
      br.appendChild(document.createTextNode(String(x.r)));
      body.appendChild(br);
    }
    li.appendChild(tile);
    li.appendChild(body);
    return li;
  }

  /* The JSON rows go into their decades, between the page's rows, by their place in the whole list (o). */
  function insert(items) {
    var byDec = {}, add = [];
    groups.forEach(function (g) { byDec[g.key] = g; });
    items.forEach(function (x) {
      var li = buildRow(x);
      var g = li && byDec[li.getAttribute("data-dec")];
      if (g && g.ol) add.push({ g: g, li: li, o: Number(li.getAttribute("data-o")) });
    });
    add.sort(function (p, q) { return p.o - q.o; });
    groups.forEach(function (g) {
      if (!g.ol) return;
      var have = Array.prototype.filter.call(g.ol.children, function (c) { return c.classList.contains("pw-arc-row"); });
      var i = 0;
      add.forEach(function (it) {
        if (it.g !== g) return;
        while (i < have.length && Number(have[i].getAttribute("data-o")) < it.o) i++;
        g.ol.insertBefore(it.li, have[i] || null);
      });
    });
    collect();
  }

  /* ---------- render ---------- */
  function setCount(chip, n) {
    if (!chip) return;
    var nEl = chip.querySelector("[data-n]");
    if (nEl) nEl.textContent = num(n);
    chip.classList.toggle("is-zero", n === 0);
  }
  function statusText(total) {
    var since = (C.since || {})[st.pub] || (C.since || {}).all;
    var when = st.dec === "undated" ? S["archive.when.undated"]
      : st.dec !== "all" ? fill(S["archive.when.dec"], { d: st.dec })
      : since ? fill(S["archive.when.since"], { year: since }) : "";
    var t = fill(S["archive.status." + (st.scope === "neta65" ? "neta65" : "texas") + (total === 1 ? ".one" : ".other")], { n: num(total), when: when }).trim();
    if (st.pub !== "all") t += fill(S["status.pub"], { pub: (C.pubs || {})[st.pub] || st.pub });
    if (st.q.trim()) t += fill(S["status.q"], { q: st.q.trim() });
    return t;
  }

  function render(opts) {
    opts = opts || {};
    // the rest of Texas is asked for but not on the page (yet): what is here still shows, the result line
    // says what is going on, and the decade chips count from the build while it loads (no search) — once it
    // has failed, the rows that are here, like the headings and "Show all N"
    var partial = needRest() && !loaded;
    var toks = tokens(st.q), total = 0, shown = 0, mtShown = false;
    root.setAttribute("data-scope", st.scope);
    groups.forEach(function (g) {
      var matched = 0, vis = 0;
      g.rows.forEach(function (r) {
        var ok = match(r, st, toks);
        var v = ok && shown < showN;
        if (ok) { matched++; total++; }
        if (v) { shown++; vis++; if (r.mt) mtShown = true; }
        if (r.el.hidden !== !v) r.el.hidden = !v;
      });
      g.el.hidden = vis === 0;
      if (g.n) g.n.textContent = stories(matched);
    });
    if (mtNote) mtNote.hidden = !mtShown;

    var base = (C.counts || {})[st.scope === "neta65" ? "neta65" : "texas"] || {};
    Array.prototype.forEach.call(decRadios, function (r) {
      r.checked = r.value === st.dec;
      var n = partial && !failed && !st.q.trim() ? Number((base[st.pub] || {})[r.value]) || 0 : count({ dec: r.value });
      setCount(r.closest(".pw-chip"), n);
    });
    Array.prototype.forEach.call(places, function (b) { setCount(b, count({ q: b.getAttribute("data-arc-place") || "" })); });

    var text = partial ? (failed ? S["archive.load_error"] : S["archive.loading"]) : total ? statusText(total) : S["archive.empty_title"];
    if (statusEl && statusEl.textContent !== text) statusEl.textContent = text;
    if (retryBtn) retryBtn.hidden = !(partial && failed);
    list.setAttribute("aria-busy", partial && loading ? "true" : "false");
    if (note) note.hidden = st.scope !== "all";

    // nothing matches: say so, with the ways out — and a help line for the cause: a search (another spelling, a
    // nearby town) or, with none, the decade and magazine (La Viña's online archive starts in 1996)
    if (emptyEl) {
      var empty = !partial && total === 0;
      emptyEl.hidden = !empty;
      if (empty) {
        var help = st.q.trim() ? S["archive.empty_text"] : st.dec !== "all" || st.pub !== "all" ? S["archive.empty_filters"] : "";
        var helpEl = emptyEl.querySelector("[data-arc-empty-text]");
        if (helpEl) { if (helpEl.textContent !== (help || "")) helpEl.textContent = help || ""; helpEl.hidden = !help; }
        var b1 = emptyEl.querySelector("[data-arc-clear]"), b2 = emptyEl.querySelector("[data-arc-alldec]"),
            b3 = emptyEl.querySelector("[data-arc-texas]"), b4 = emptyEl.querySelector("[data-arc-allpub]");
        if (b1) b1.hidden = !st.q.trim();
        if (b2) b2.hidden = st.dec === "all";
        if (b3) b3.hidden = st.scope !== "neta65";
        if (b4) b4.hidden = st.pub === "all";
      }
    }

    // "Show 40 more" (when more than 40 are left) / "Show all N", "Showing 40 of N"
    var left = total - shown;
    if (more) {
      more.hidden = !(left > 0);
      if (left > 0) {
        if (pageBtn) {
          pageBtn.hidden = left <= PAGE;
          var l1 = pageBtn.querySelector("[data-label]");
          if (l1) l1.textContent = fill(S.show_more, { k: num(PAGE) });
        }
        var l2 = allBtn && allBtn.querySelector("[data-label]");
        if (l2) l2.textContent = fill(S.show_all, { n: num(total) });
        if (shownNote) shownNote.textContent = fill(S.shown_of, { shown: num(shown), n: num(total) });
      }
    }
    if (!opts.keepUrl) writeUrl();
  }

  function update(opts) {
    if (needRest() && !loaded && !loading && !failed) load();
    render(opts);
  }

  /* ---------- the page's search box (published.js applies it to the whole page) ---------- */
  function search(q) {
    if (form && qInput && !qInput.disabled) {
      qInput.value = q;
      try {
        qInput.dispatchEvent(new Event("input", { bubbles: true }));                 // published.js: the clear button
        form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })); // …and at once, not after a pause
        return;
      } catch (e) { /* an old browser: below */ }
    }
    st.q = q;
    showN = PAGE;
    update();
  }
  function reducedMotion() {
    try { return window.GV && window.GV.reducedMotion ? window.GV.reducedMotion() : window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) { return false; }
  }
  function reveal() {
    var head = $("pw-arc-title") || root;
    var top = head.getBoundingClientRect().top;
    if (top < 0 || top > window.innerHeight * 0.6) head.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "start" });
  }
  function focusDecade() {
    var r = root.querySelector('input[name="pw-dec"]:checked');
    if (r) r.focus();
  }
  /* After "Show 40 more": keyboard focus goes to the first story that just appeared (its link). */
  function focusFirstNew(before) {
    for (var i = 0; i < rows.length; i++) {
      if (!before[i] && !rows[i].el.hidden) {
        var a = rows[i].el.querySelector("a");
        if (a) { a.focus(); return; }
      }
    }
  }

  /* ---------- events ---------- */
  document.addEventListener("pw:state", function (e) {
    var prev = st.scope;
    fromPage(e && e.detail && e.detail.state);
    if (st.scope !== prev) failed = false;   // another scope: a download that failed is tried again
    showN = PAGE;
    update();
  });
  document.addEventListener("pw:reset", function () {
    st.dec = "all";
    showN = PAGE;
    update();
  });
  root.addEventListener("change", function (e) {
    var t = e.target;
    if (!t || t.name !== "pw-dec" || !DECS[t.value]) return;
    st.dec = t.value;
    showN = PAGE;
    update();
  });
  root.addEventListener("click", function (e) {
    var b = e.target.closest ? e.target.closest("button") : null;
    if (!b || b.disabled) return;
    if (b.hasAttribute("data-arc-place")) {
      search(b.getAttribute("data-arc-place") || "");
      reveal();
    } else if (b.hasAttribute("data-arc-more")) {
      var before = rows.map(function (r) { return !r.el.hidden; });
      showN = b.getAttribute("data-arc-more") === "all" ? Infinity : showN + PAGE;
      render({ keepUrl: true });
      focusFirstNew(before);
    } else if (b.hasAttribute("data-arc-retry")) {
      failed = false;
      update({ keepUrl: true });
      // the button hides itself while loading: keyboard focus goes to the decade chosen, not to <body>
      focusDecade();
    } else if (b.hasAttribute("data-arc-clear")) {
      search("");
      // the reader stays at the archive (the search box is far up the page, and visibly empty now)
      focusDecade();
    } else if (b.hasAttribute("data-arc-alldec")) {
      st.dec = "all";
      showN = PAGE;
      update();
      focusDecade();
    } else if (b.hasAttribute("data-arc-texas")) {
      choose("scope", "texas");
      focusDecade();
    } else if (b.hasAttribute("data-arc-allpub")) {
      choose("pub", "all");
      focusDecade();
    }
  });
  /* A choice of the page's filter card made from here (published.js applies it to the whole page). */
  function choose(name, value) {
    var r = form && form.querySelector('input[name="' + name + '"][value="' + value + '"]');
    if (r && !r.disabled) {
      r.checked = true;
      r.dispatchEvent(new Event("change", { bubbles: true }));
    } else {
      st[name] = value;
      showN = PAGE;
      update();
    }
  }
  // Back / Forward over the page's own links (#archive): that history entry's address is older than the decade
  // on screen — put the decade back into it (published.js does the same for its own keys)
  window.addEventListener("popstate", function () { writeUrl(); });

  /* ---------- start ---------- */
  readUrl();
  // the controls start disabled (useless without this script); switch them on
  Array.prototype.forEach.call(root.querySelectorAll("[data-arc-ctl]"), function (c) { c.disabled = false; });
  update();
  // the rows past the first 40 were listed for readers without JavaScript; render() has given every row
  // and decade its own `hidden` now, so the first-paint rule (published.css) can go
  Array.prototype.forEach.call(list.querySelectorAll("[data-pw-over]"), function (x) { x.removeAttribute("data-pw-over"); });
  // A link to #archive: the lists above it may have changed height since the browser scrolled there.
  if (location.hash === "#archive") { var sec = $("archive"); if (sec) sec.scrollIntoView({ block: "start" }); }
})();
