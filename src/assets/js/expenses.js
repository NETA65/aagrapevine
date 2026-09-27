/* The service expense tracker on /expenses/ (src/pages/expenses.njk): the page's Alpine app, "xpApp".
   The data model, the money math, the summaries, CSV and backups live in expenses-core.js (window.GVX,
   loaded just before this file; tests/test_expenses_core.py). This file is the screen:
     · five views in a tab bar — Entries · Summary · Giveaways · Requests · Settings — remembered in the
       settings (ui.view) and in the address (#entries …), so links and the back button work;
     · the add / edit dialog (a native <dialog>), bulk changes with a 10-second undo;
     · the reimbursement request (print / copy / share / CSV / "mark as submitted") and the year summary;
     · import (CSV or a full backup: preview first, then merge or replace) and export;
     · receipt photos.
   Storage — only in this browser, as the page promises:
     localStorage "gv-expenses:v1"         {v, entries, settings, meta} (GVX owns the shape; migrate on load)
     localStorage "gv-expenses:v1:ui"      {view, period, sort, from, to}: the screen's own conveniences,
                                           apart, so a tab click never looks like new data to another tab
     IndexedDB "gv-expenses" / "receipts"  one photo per entry (key = the entry id), a downscaled JPEG;
                                           a photo no entry points to any more is deleted on load
   Every storage call is wrapped: in a private window (or with storage blocked, or full) the app still
   works in memory, warns to export before closing, and never says "Saved" for something it could not
   keep. A change made in another tab reloads the data here.
   The entries live OUTSIDE Alpine's reactive proxies, so 5,000 of them stay fast: `rev` goes up on every
   change and each view is computed once per change (memo()), never once per row.
   Never x-html: every text goes through x-text; icons come from the build (#xp-icons → x-xp-icon).
   The app's words come from <script id="xp-ui"> (src/_i18n/expenses.json, page language, without the
   "expenses." prefix); the defaults from <script id="xp-config"> (config/expenses.yml). */
(function () {
  "use strict";
  var GV = window.GV || {};
  var KEY = "gv-expenses:v1";
  var UI_KEY = KEY + ":ui";
  var DB_NAME = "gv-expenses";
  var DB_STORE = "receipts";
  var PAGE = 100;              // rows per "Show more"
  var UNDO_MS = 10000;         // how long "Undo" stays after a delete (paused while the toast has the focus or the mouse)
  var MAX_PHOTO = 1600;        // longest side of a stored receipt photo (px)
  var VIEWS = ["entries", "summary", "giveaways", "requests", "settings"];
  var TYPES = ["expense", "mileage", "received", "giveaway", "stock"];
  var CLAIMS = ["to_request", "submitted", "paid", "denied"];
  var SET_TABS = ["data", "profile", "categories", "funders", "methods", "mileage", "budgets", "fields", "reminders"];
  var TYPE_ICON = { expense: "receipt", mileage: "car", received: "banknote", giveaway: "heart-handshake", stock: "package" };
  var STATUS_ICON = { none: "hand-heart", to_request: "clock", submitted: "send", paid: "circle-check", denied: "circle-x" };
  var SORTS = { date_desc: ["date", "desc"], date_asc: ["date", "asc"], amount_desc: ["amount", "desc"], amount_asc: ["amount", "asc"], category: ["category", "asc"], updated: ["updated", "desc"] };

  /* ---------------- small helpers ---------------- */
  function fmt(tpl, vars) {
    return String(tpl == null ? "" : tpl).replace(/\{(\w+)\}/g, function (m, k) { return vars && vars[k] != null ? String(vars[k]) : m; });
  }
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function isoOf(d) { return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); }
  function today() { return isoOf(new Date()); }
  function nowIso() { return new Date().toISOString(); }
  function daysSince(iso) { if (!iso) return null; var t = Date.parse(iso.length === 10 ? iso + "T12:00:00" : iso); return isNaN(t) ? null : Math.floor((Date.now() - t) / 864e5); }
  function clone(o) { return o == null ? o : JSON.parse(JSON.stringify(o)); }
  function str(v) { return v == null ? "" : String(v); }
  function clean(s) { return str(s).replace(/\s+/g, " ").trim(); }
  // case-, accent- and space-insensitive (matching names typed on different devices)
  function norm(s) { return clean(s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, ""); }
  function num(v) { if (v === "" || v == null) return ""; var n = Number(String(v).replace(",", ".")); return isFinite(n) ? n : ""; }
  function cents2str(c) { return c === "" || c == null || isNaN(c) ? "" : (Number(c) / 100).toFixed(2); }
  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } }
  function lsDel(k) { try { localStorage.removeItem(k); return true; } catch (e) { return false; } }
  function storageWorks() {
    try { var k = KEY + ":probe"; localStorage.setItem(k, "1"); localStorage.removeItem(k); return true; } catch (e) { return false; }
  }
  function uniq(list) {
    var seen = {}, out = [];
    list.forEach(function (v) { var s = clean(v), n = norm(s); if (s && !seen[n]) { seen[n] = 1; out.push(s); } });
    return out;
  }
  // Focus an element as soon as it is displayed (an x-show that has not been applied yet: a few frames).
  function focusShown(el, tries) {
    if (!el) return;
    if (el.offsetParent !== null || el.getClientRects().length) { el.focus(); return; }
    if ((tries || 0) < 10) requestAnimationFrame(function () { focusShown(el, (tries || 0) + 1); });
  }
  function safeName(s) { return norm(s).replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 32); }

  /* The date range of a period: this / last month, this / last year, a service panel ("panel:77"),
     everything (""), or the visitor's own dates. Inclusive ISO days. */
  function periodRange(p, panels, from, to) {
    var d = new Date(), y = d.getFullYear(), m = d.getMonth();
    if (p === "this_month") return { from: isoOf(new Date(y, m, 1)), to: isoOf(new Date(y, m + 1, 0)) };
    if (p === "last_month") return { from: isoOf(new Date(y, m - 1, 1)), to: isoOf(new Date(y, m, 0)) };
    if (p === "this_year") return { from: y + "-01-01", to: y + "-12-31" };
    if (p === "last_year") return { from: (y - 1) + "-01-01", to: (y - 1) + "-12-31" };
    if (p && p.indexOf("panel:") === 0) {
      var id = p.slice(6), hit = (panels || []).filter(function (x) { return x.id === id; })[0];
      if (hit) return { from: hit.from, to: hit.to };
    }
    if (p === "custom") return { from: from || "", to: to || "" };
    return { from: "", to: "" };
  }

  /* ---------------- receipts: IndexedDB (one photo per entry) ---------------- */
  var dbP = null;
  function idb() {
    if (dbP) return dbP;
    dbP = new Promise(function (res, rej) {
      if (!window.indexedDB) return rej(new Error("idb"));
      var r;
      try { r = indexedDB.open(DB_NAME, 1); } catch (e) { return rej(e); }
      r.onupgradeneeded = function () { if (!r.result.objectStoreNames.contains(DB_STORE)) r.result.createObjectStore(DB_STORE, { keyPath: "id" }); };
      r.onsuccess = function () { res(r.result); };
      r.onerror = function () { rej(r.error); };
      r.onblocked = function () { rej(new Error("blocked")); };
    });
    dbP.catch(function () { dbP = null; });
    return dbP;
  }
  function idbRun(mode, fn) {
    return idb().then(function (db) {
      return new Promise(function (res, rej) {
        var tx = db.transaction(DB_STORE, mode), req = fn(tx.objectStore(DB_STORE));
        tx.oncomplete = function () { res(req ? req.result : undefined); };
        tx.onerror = function () { rej(tx.error); };
        tx.onabort = function () { rej(tx.error); };
      });
    });
  }
  var photos = {
    get: function (id) { return idbRun("readonly", function (s) { return s.get(id); }).catch(function () { return null; }); },
    put: function (rec) { return idbRun("readwrite", function (s) { return s.put(rec); }); },
    del: function (id) { return idbRun("readwrite", function (s) { return s.delete(id); }).catch(function () {}); },
    all: function () { return idbRun("readonly", function (s) { return s.getAll(); }).catch(function () { return []; }); },
    keys: function () { return idbRun("readonly", function (s) { return s.getAllKeys(); }).catch(function () { return []; }); },
    clear: function () { return idbRun("readwrite", function (s) { return s.clear(); }).catch(function () {}); },
  };
  // A photo from the camera or the gallery → a JPEG no longer than MAX_PHOTO on its longest side.
  function shrinkPhoto(file) {
    return new Promise(function (res, rej) {
      var url = URL.createObjectURL(file), img = new Image();
      img.onload = function () {
        var w = img.naturalWidth, h = img.naturalHeight, k = Math.min(1, MAX_PHOTO / Math.max(w, h, 1));
        var c = document.createElement("canvas");
        c.width = Math.max(1, Math.round(w * k)); c.height = Math.max(1, Math.round(h * k));
        var g = c.getContext("2d");
        g.fillStyle = "#fff"; g.fillRect(0, 0, c.width, c.height);
        g.drawImage(img, 0, 0, c.width, c.height);
        URL.revokeObjectURL(url);
        c.toBlob(function (b) { if (b) res({ blob: b, w: c.width, h: c.height }); else rej(new Error("photo")); }, "image/jpeg", 0.8);
      };
      img.onerror = function () { URL.revokeObjectURL(url); rej(new Error("photo")); };
      img.src = url;
    });
  }
  function blobToDataUrl(blob) {
    return new Promise(function (res) { var r = new FileReader(); r.onload = function () { res(String(r.result)); }; r.onerror = function () { res(""); }; r.readAsDataURL(blob); });
  }
  function dataUrlToBlob(u) {
    var m = /^data:([^;,]+)?(;base64)?,(.*)$/.exec(u || "");
    if (!m) return null;
    try {
      var bin = m[2] ? atob(m[3]) : decodeURIComponent(m[3]), a = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) a[i] = bin.charCodeAt(i);
      return new Blob([a], { type: m[1] || "image/jpeg" });
    } catch (e) { return null; }
  }

  /* ---------------- files and the clipboard ---------------- */
  function saveBlob(blob, name) {
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
  }
  // A file's text. Read as bytes and decoded by GVX.decodeText: UTF-8, or Windows-1252 when the file
  // is not valid UTF-8 (Excel's "CSV" on Windows), so accented names never turn into "�".
  function readText(file) {
    var X = window.GVX;
    var bytes = file.arrayBuffer ? file.arrayBuffer() : new Promise(function (res, rej) {
      var r = new FileReader(); r.onload = function () { res(r.result); }; r.onerror = function () { rej(r.error); }; r.readAsArrayBuffer(file);
    });
    return bytes.then(function (buf) { return X && X.decodeText ? X.decodeText(new Uint8Array(buf)) : new TextDecoder("utf-8").decode(buf); });
  }
  function legacyCopy(text) {
    var back = document.activeElement, ta = document.createElement("textarea"), ok = false;
    ta.value = text; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0"; ta.style.top = "0";
    (document.querySelector("dialog[open]") || document.body).appendChild(ta);
    ta.select();
    try { ok = document.execCommand("copy") !== false; } catch (e) { ok = false; }
    ta.remove();
    if (back && back.focus) back.focus({ preventScroll: true });
    return ok;
  }
  function writeText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText && window.isSecureContext) {
      return navigator.clipboard.writeText(text).catch(function () { return legacyCopy(text) ? true : Promise.reject(new Error("copy")); });
    }
    return legacyCopy(text) ? Promise.resolve(true) : Promise.reject(new Error("copy"));
  }

  /* ---------------- icons: drawn once at build time (#xp-icons), looked up by name ---------------- */
  var ICONS = null;
  function iconHtml(name) {
    if (!ICONS) {
      ICONS = {};
      var box = document.getElementById("xp-icons");
      if (box) box.querySelectorAll("[data-i]").forEach(function (el) { ICONS[el.getAttribute("data-i")] = el.innerHTML; });
    }
    return ICONS[name] || ICONS.shapes || "";
  }

  document.addEventListener("alpine:init", function () {
    var Alpine = window.Alpine;
    // x-xp-icon="expr": the site's own icon markup for a name from our list (never the visitor's text)
    Alpine.directive("xp-icon", function (el, d, u) {
      var get = u.evaluateLater(d.expression);
      u.effect(function () { get(function (n) { var h = iconHtml(String(n || "")); if (el.innerHTML !== h) el.innerHTML = h; }); });
    });

    Alpine.data("xpApp", function (pageLang) {
      // Outside Alpine's reactivity (see the header): the data, the memo cache, timers, the pending photo.
      var S = { X: null, cfg: null, ui: {}, state: null, memo: {}, undo: null, undoT: 0, toastT: 0, flashT: 0,
                askResolve: null, opener: null, formSnap: "", photo: null, photoUrl: "", rqUrls: [], persistTried: false,
                siteEvents: [] };

      return {
        L: pageLang === "es" ? "es" : "en",
        ready: false,
        broken: false,
        rev: 0,
        view: "entries",
        storageOk: true,
        persisted: null,
        usage: null,
        wide: true,
        // Entries: filters (the period is shared with Summary), sort, paging, selection
        f: { q: "", period: "this_year", from: "", to: "", types: [], category: "", funder: "", status: "", event: "", tag: "", receipt: "" },
        moreFilters: false,
        sort: "date_desc",
        shown: PAGE,
        sel: {},
        bulkFunder: "",
        bulkCat: "",
        flashId: "",
        toastMsg: "",
        toastUndo: false,
        // the add / edit dialog
        form: null,
        formStep: 1,
        formMode: "add",
        formErr: {},
        formErrs: [],
        formMore: false,
        photoUrl: "",
        photoBusy: false,
        dlgMsg: "",               // the dialog's own status line (the page's toast is behind the modal)
        // Requests
        rq: { funder: "", period: "this_year", from: "", to: "", st: { to_request: true, submitted: false, paid: false, denied: false }, names: false, photos: false, ref: "" },
        rqPhotos: [],
        yr: new Date().getFullYear(),
        // Settings
        setTab: "data",
        open: {},
        newCatType: "expense",
        newPlace: "",
        imp: null,
        dragOver: false,
        eraseText: "",
        ask: { msg: "", ok: "", danger: false },

        /* ================= start-up ================= */
        init: function () {
          var self = this;
          try {
            S.cfg = JSON.parse(document.getElementById("xp-config").textContent);
            S.ui = JSON.parse(document.getElementById("xp-ui").textContent) || {};
            var ev = document.getElementById("xp-events");
            S.siteEvents = ev ? JSON.parse(ev.textContent) || [] : [];
          } catch (e) { S.cfg = null; }
          S.X = window.GVX;
          if (!S.cfg || !S.X || typeof S.X.emptyState !== "function") { this.broken = true; return; }
          this.storageOk = storageWorks();
          try { this.loadState(); } catch (e) { if (window.console) console.error("[expenses]", e); this.broken = true; return; }
          var u = {};
          try { u = JSON.parse(lsGet(UI_KEY) || "null") || this.st().ui || {}; } catch (e) { u = {}; }
          if (u.period) this.f.period = u.period;
          if (u.sort && SORTS[u.sort]) this.sort = u.sort;
          if (u.from) this.f.from = u.from;
          if (u.to) this.f.to = u.to;
          this.rq.period = this.f.period;
          this.view = this.hashView() || (VIEWS.indexOf(u.view) !== -1 ? u.view : "entries");
          if (this.view === "requests") this.rq.funder = this.rqBestFunder();
          this.fitList();
          this.checkStorage();
          this.ready = true;
          // the address and the back button
          var onHash = function () { var v = self.hashView(); if (v && v !== self.view) self.go(v, false); };
          window.addEventListener("hashchange", onHash);
          window.addEventListener("popstate", onHash);
          // table ↔ cards: the width and the text size (the "Aa" panel)
          if (window.matchMedia) {
            var mq = window.matchMedia("(min-width: 48rem)");
            if (mq.addEventListener) mq.addEventListener("change", function () { self.fitList(); });
          }
          window.addEventListener("gvlv:prefs", function () { self.fitList(); });
          // an edit in another tab on this device (the page's toast is behind an open dialog: the
          // dialog says it; an entry being edited there that the other tab deleted is saved as a new one)
          window.addEventListener("storage", function (e) {
            if (e.key !== KEY) return;
            self.loadState();
            if (!self.form) { self.say(self.t("toast.other_tab")); return; }
            var id = self.form.id, gone = self.formMode === "edit" && id && !S.state.entries.some(function (x) { return x.id === id; });
            if (gone) { self.formMode = "add"; self.form.id = ""; self.form.created = ""; }
            self.dlgMsg = "";
            self.$nextTick(function () { self.dlgMsg = self.t(gone ? "form.deleted_elsewhere" : "toast.other_tab"); });
          });
          this.$watch("f", function () { self.shown = PAGE; });
          // receipt photos no entry points to (a delete whose undo time never ran out, a CSV "replace") —
          // only when the ledger was read from this browser (never on an empty or unreadable one)
          setTimeout(function () { if (self.storageOk && S.readOk) self.cleanPhotos(); }, 1500);
        },
        hashView: function () {
          var h = (location.hash || "").replace(/^#/, "");
          return VIEWS.indexOf(h) !== -1 ? h : "";
        },
        fitList: function () {
          var big = /^(130|150)$/.test(document.documentElement.getAttribute("data-text") || "");
          var w = window.matchMedia ? window.matchMedia("(min-width: 48rem)").matches : true;
          this.wide = w && !big;
        },

        /* ================= storage ================= */
        loadState: function () {
          var X = S.X, raw = lsGet(KEY), st = null;
          if (raw) {
            try { st = X.migrate(JSON.parse(raw), S.cfg); } catch (e) { st = null; }
            // never overwrite what we could not read: keep a copy beside it
            if (!st) lsSet(KEY + ":unreadable-" + today(), raw);
          }
          S.readOk = !!(raw && st);    // the ledger really came from this browser (cleanPhotos trusts only that)
          if (!st || typeof st !== "object") st = X.emptyState(S.cfg);
          st.entries = Array.isArray(st.entries) ? st.entries : [];
          st.settings = X.mergeDefaults(S.cfg, st.settings || {});
          st.meta = st.meta || { lastBackup: null, lastExport: null, created: nowIso() };
          S.state = st;
          S.memo = {};
          this.rev++;
        },
        // Writes the data; false when the browser would not keep it (the warning shows, and stays until
        // a save works again — space freed, for one).
        save: function () {
          var ok = lsSet(KEY, JSON.stringify(S.state));
          this.storageOk = ok;
          S.saveOk = ok;
          S.memo = {};
          this.rev++;
          return ok;
        },
        // the message after a change: never "Saved" (or "Deleted" …) when the last save failed
        saySaved: function (msg, withUndo) { this.say(S.saveOk === false ? this.t("storage_off") : msg, withUndo); },
        saveUi: function () {
          lsSet(UI_KEY, JSON.stringify({ period: this.f.period, sort: this.sort, view: this.view, from: this.f.from, to: this.f.to }));
        },
        // Ask the browser not to clear our data on its own (once a session, after an entry is saved).
        askPersist: function () {
          var self = this;
          if (S.persistTried || this.persisted) return;
          S.persistTried = true;
          try { navigator.storage.persist().then(function (v) { self.persisted = !!v; }, function () {}); } catch (e) { /* not supported */ }
        },
        checkStorage: function () {
          var self = this;
          try { navigator.storage.persisted().then(function (v) { self.persisted = !!v; }, function () { self.persisted = false; }); } catch (e) { this.persisted = false; }
          try { navigator.storage.estimate().then(function (e) { self.usage = e && e.usage != null ? e.usage : null; }, function () {}); } catch (e) { /* not supported */ }
        },

        /* ================= words, numbers, dates ================= */
        t: function (k, vars) { var s = S.ui[k]; return fmt(s == null ? k : s, vars); },
        // a message key from the core ("expenses.err.x") → its text
        msgKey: function (k) { return this.t(String(k || "").replace(/^expenses\./, "")); },
        lbl: function (x) {
          if (x == null) return "";
          if (typeof x === "string") return x;
          return x[this.L] || x.en || x.es || "";
        },
        money: function (c) {
          c = Number(c) || 0;
          try { if (S.X.fmtMoney) return S.X.fmtMoney(c, this.L); } catch (e) { /* fall through */ }
          return new Intl.NumberFormat(this.L === "es" ? "es-US" : "en-US", { style: "currency", currency: "USD" }).format(c / 100);
        },
        count: function (n) { return new Intl.NumberFormat(this.L === "es" ? "es-US" : "en-US", { maximumFractionDigits: 1 }).format(Number(n) || 0); },
        plural: function (n, one, many) { return this.t(Number(n) === 1 ? one : many, { n: this.count(n) }); },
        day: function (iso, long) {
          if (!iso) return "";
          // long: "September 27, 2026" · "mid": "Sep 27, 2026" (the printed request) · else "Sep 27" (+ the year when not this year)
          var o = long === true ? { month: "long", day: "numeric", year: "numeric" } : { month: "short", day: "numeric" };
          if (long === "mid" || (!long && iso.slice(0, 4) !== String(new Date().getFullYear()))) o.year = "numeric";
          var s = GV.fmtDate ? GV.fmtDate(iso.slice(0, 10) + "T12:00:00Z", o) : iso;
          return s || iso;
        },
        ago: function (isoTime) {
          if (!isoTime) return this.t("aside.never");
          var d = daysSince(isoTime);
          if (d === 0) return this.t("time.today");
          if (d === 1) return this.t("time.yesterday");
          return this.t("time.days_ago", { n: this.count(d) });
        },
        rateText: function (r) { return r === "" || r == null ? this.t("form.rate_unset") : this.t("form.rate_value", { rate: String(r) }); },

        /* ================= the data ================= */
        // reading `rev` makes every binding that uses the settings follow their changes
        st: function () { this.rev; return S.state ? S.state.settings : {}; },
        E: function () { this.rev; return S.state ? S.state.entries : []; },
        memo: function (name, key, fn) {
          var k = this.rev + "|" + key, m = S.memo[name];
          if (m && m.k === k) return m.v;
          var v;
          try { v = fn.call(this); } catch (e) { if (window.console) console.error("[expenses]", name, e); v = null; }
          S.memo[name] = { k: k, v: v };
          return v;
        },
        maps: function () {
          return this.memo("maps", "", function () {
            var s = this.st(), m = { cat: {}, fun: {}, met: {} };
            (s.categories || []).forEach(function (c) { m.cat[c.id] = c; });
            (s.funders || []).forEach(function (f) { m.fun[f.id] = f; });
            (s.methods || []).forEach(function (x) { m.met[x.id] = x; });
            return m;
          }) || { cat: {}, fun: {}, met: {} };
        },
        cat: function (id) { return this.maps().cat[id] || null; },
        catLabel: function (id) { var c = this.cat(id); return c ? this.lbl(c.label) : (id || this.t("list.no_category")); },
        catIcon: function (id) { var c = this.cat(id); return c && c.icon ? c.icon : "shapes"; },
        catTone: function (id) { var c = this.cat(id); return "xp-tone-" + (c && c.color ? c.color : "slate"); },
        funder: function (id) { return this.maps().fun[id] || null; },
        funderName: function (id) { var f = this.funder(id); return f ? this.lbl(f.name) : (id || ""); },
        isSelf: function (id) { var f = this.funder(id); return !id || id === "me" || !!(f && f.kind === "self"); },
        methodName: function (id) { var m = this.maps().met[id]; return m ? this.lbl(m.name) : (id || ""); },
        byOrder: function (a, b) { return (a.order || 0) - (b.order || 0); },
        // lists for the selects: visible ones in their order (plus the one an entry already uses)
        cats: function (type, keep) {
          return (this.st().categories || []).filter(function (c) { return c.type === type && (!c.hidden || c.id === keep); }).slice().sort(this.byOrder);
        },
        funders: function (keep, kinds) {
          return (this.st().funders || []).filter(function (f) { return (!f.hidden || f.id === keep) && (!kinds || kinds.indexOf(f.kind) !== -1); }).slice().sort(this.byOrder);
        },
        claimFunders: function () { var self = this; return this.funders(this.rq.funder).filter(function (f) { return !self.isSelf(f.id); }); },
        people: function () { return this.funders("", ["person"]); },
        methods: function (keep) { return (this.st().methods || []).filter(function (m) { return !m.hidden || m.id === keep; }).slice().sort(this.byOrder); },
        rates: function () { return this.st().rates || []; },
        defaultRate: function () {
          var s = this.st(), id = s.default_rate || (s.defaults && s.defaults.rate), list = this.rates();
          return list.filter(function (r) { return r.id === id; })[0] || list[0] || { id: "", rate: "" };
        },
        panels: function () { return this.st().panels || S.cfg.panels || []; },
        usedCount: function (field, id) {
          var m = this.memo("used:" + field, "", function () {
            var o = {};
            S.state.entries.forEach(function (e) { var v = e[field]; if (v) o[v] = (o[v] || 0) + 1; });
            return o;
          }) || {};
          return m[id] || 0;
        },
        hasExamples: function () { return this.E().some(function (e) { return e.example; }); },

        /* ================= the tab bar ================= */
        go: function (v, push) {
          if (VIEWS.indexOf(v) === -1) return;
          this.view = v;
          if (v === "requests" && !this.rq.funder) this.rq.funder = this.rqBestFunder();
          if (push !== false) {
            try { history.pushState(null, "", "#" + v); } catch (e) { /* file:// or sandboxed */ }
          }
          this.saveUi();
        },
        // Arrow keys move between the tabs (and open them), Home / End jump to the ends.
        tabKey: function (e) {
          var i = VIEWS.indexOf(this.view), n = VIEWS.length, j = -1;
          if (e.key === "ArrowRight") j = (i + 1) % n;
          else if (e.key === "ArrowLeft") j = (i - 1 + n) % n;
          else if (e.key === "Home") j = 0;
          else if (e.key === "End") j = n - 1;
          if (j < 0) return;
          e.preventDefault();
          this.go(VIEWS[j]);
          var b = document.getElementById("xp-tab-" + VIEWS[j]);
          if (b) { b.focus(); if (b.scrollIntoView) b.scrollIntoView({ block: "nearest", inline: "nearest" }); }
        },

        /* ================= periods and filters ================= */
        periods: function () {
          var self = this, out = ["this_month", "last_month", "this_year", "last_year"].map(function (p) { return { id: p, label: self.t("period." + p) }; });
          this.panels().forEach(function (p) { out.push({ id: "panel:" + p.id, label: self.t("period.panel", { n: p.id }) }); });
          out.push({ id: "all", label: self.t("period.all") }, { id: "custom", label: self.t("period.custom") });
          return out;
        },
        range: function (p, from, to) {
          if (p === undefined) { p = this.f.period; from = this.f.from; to = this.f.to; }
          return periodRange(p, this.panels(), from, to);
        },
        setPeriod: function (p) { this.f.period = p; this.rq.period = p; this.saveUi(); },
        toggleType: function (t) {
          var i = this.f.types.indexOf(t);
          if (i === -1) this.f.types.push(t); else this.f.types.splice(i, 1);
        },
        typeOn: function (t) { return this.f.types.indexOf(t) !== -1; },
        moreCount: function () { var f = this.f; return ["category", "funder", "status", "event", "tag", "receipt"].filter(function (k) { return f[k] !== ""; }).length; },
        anyFilter: function () { return !!(this.f.q || this.f.types.length || this.moreCount()); },
        clearFilters: function () {
          var f = this.f;
          f.q = ""; f.types = []; f.category = ""; f.funder = ""; f.status = ""; f.event = ""; f.tag = ""; f.receipt = "";
        },
        filtered: function () {
          var f = this.f, key = JSON.stringify(f) + "|" + this.sort;
          return this.memo("filtered", key, function () {
            var X = S.X, r = this.range();
            var q = { q: clean(f.q), types: f.types.slice(), categories: f.category ? [f.category] : [], funders: f.funder ? [f.funder] : [],
                      statuses: f.status ? [f.status] : [], event: f.event, tag: f.tag, from: r.from, to: r.to };
            if (f.receipt !== "") q.hasReceipt = f.receipt === "yes";
            var list = X.filterEntries(S.state.entries, q, this.st()) || [];
            var s = SORTS[this.sort] || SORTS.date_desc;
            return X.sortEntries(list, s[0], s[1], this.st()) || list;
          }) || [];
        },
        // the period alone (the "N more outside this period" hint)
        inPeriodCount: function () {
          var f = this.f;
          return this.memo("inPeriod", JSON.stringify(f), function () {
            var r = this.range();
            return S.X.filterEntries(S.state.entries, { from: r.from, to: r.to }).length;
          }) || 0;
        },
        listSum: function () {
          var key = JSON.stringify(this.f);
          return this.memo("listSum", key, function () { return S.X.summary(this.filtered(), this.st(), {}); }) || {};
        },
        countLine: function () {
          var n = this.filtered().length, s = this.listSum();
          return this.t("list.count_line", { entries: this.plural(n, "list.entries_one", "list.entries"), spent: this.money(s.spent_cents), received: this.money(s.received_cents) });
        },

        /* The rows on screen: display-ready, computed once per change. */
        rows: function () {
          var key = JSON.stringify(this.f) + "|" + this.sort + "|" + this.shown;
          return this.memo("rows", key, function () {
            var self = this;
            return this.filtered().slice(0, this.shown).map(function (e) { return self.rowOf(e); });
          }) || [];
        },
        rowOf: function (e) {
          var self = this, sub = [], t = e.type, d = norm(e.description);
          var add = function (v) { if (clean(v) && d.indexOf(norm(v)) === -1) sub.push(clean(v)); };
          if (t === "mileage" && (e.from || e.to)) add(clean(e.from) + " → " + clean(e.to));
          if (e.item) add(e.item + (e.quantity !== "" && e.quantity != null && t !== "giveaway" && t !== "stock" ? " × " + self.count(e.quantity) : ""));
          add(e.person);
          add(e.event);
          if (!e.item) add(e.vendor);
          var amount, flow = "out";
          if (t === "received") { amount = "+" + self.money(e.amount_cents); flow = "in"; }
          else if (t === "giveaway") { amount = self.t("list.qty_given", { n: self.count(e.quantity || 0) }); flow = "items"; }
          else if (t === "stock") { amount = self.t("list.qty_in", { n: self.count(e.quantity || 0) }); flow = "items"; }
          else amount = self.money(e.amount_cents);
          var status = e.claim_status || "none";
          var showStatus = (t === "expense" || t === "mileage") && status !== "none";
          return {
            id: e.id, type: t, date: self.day(e.date), iso: e.date,
            desc: e.description || self.catLabel(e.category),
            sub: sub.join(" · "),
            miles: t === "mileage" ? self.t("list.miles", { n: self.count(e.miles || 0) }) : "",
            cat: self.catLabel(e.category), icon: self.catIcon(e.category), tone: self.catTone(e.category),
            funder: t === "giveaway" ? "" : self.funderName(e.funder),
            status: showStatus ? status : "", statusText: showStatus ? self.t("status." + status) : "", statusIcon: STATUS_ICON[status] || "clock",
            amount: amount, flow: flow, direct: e.method === "direct",
            receipt: e.receipt || "none", example: !!e.example,
          };
        },
        more: function () { this.shown += PAGE; },
        remaining: function () { return Math.max(0, this.filtered().length - this.shown); },

        /* ================= selection and bulk changes ================= */
        selIds: function () { var s = this.sel; return Object.keys(s).filter(function (k) { return s[k]; }); },
        selCount: function () { return this.selIds().length; },
        isSel: function (id) { return !!this.sel[id]; },
        toggleSel: function (id) { if (this.sel[id]) delete this.sel[id]; else this.sel[id] = true; },
        allShownSel: function () { var self = this, r = this.rows(); return r.length > 0 && r.every(function (x) { return self.sel[x.id]; }); },
        toggleAllShown: function () {
          var self = this, on = !this.allShownSel();
          this.rows().forEach(function (x) { if (on) self.sel[x.id] = true; else delete self.sel[x.id]; });
        },
        selectAllMatching: function () { var self = this; this.filtered().forEach(function (e) { self.sel[e.id] = true; }); },
        clearSel: function () { this.sel = {}; this.bulkFunder = ""; this.bulkCat = ""; },
        // one change to many entries: each entry is normalized again (derived fields, updated time)
        patch: function (ids, fn) {
          var X = S.X, set = {}, n = 0, st = this.st();
          ids.forEach(function (id) { set[id] = 1; });
          S.state.entries = S.state.entries.map(function (e) {
            if (!set[e.id]) return e;
            var c = clone(e);
            if (fn(c) === false) return e;
            c.updated = nowIso();
            n++;
            var r = X.normalizeEntry(c, st);
            return r && r.entry ? r.entry : c;
          });
          this.save();
          return n;
        },
        bulkStatus: function (to) {
          var self = this, d = today();
          var n = this.patch(this.selIds(), function (e) {
            if ((e.type !== "expense" && e.type !== "mileage") || self.isSelf(e.funder)) return false;
            e.claim_status = to;
            if (to === "submitted" && !e.claim_date) e.claim_date = d;
            if (to === "paid" && !e.paid_date) e.paid_date = d;
            // a purchase made for someone who pays it back: paid means repaid (the two never disagree)
            if (to === "paid" && e.repaid === "owed") e.repaid = "repaid";
          });
          this.saySaved(this.plural(n, "toast.updated_one", "toast.updated"));
        },
        bulkSetFunder: function () {
          var self = this, to = this.bulkFunder;
          if (!to) return;
          var n = this.patch(this.selIds(), function (e) {
            if (e.type === "giveaway") return false;
            e.funder = to;
            if (e.type === "expense" || e.type === "mileage") {
              if (self.isSelf(to)) e.claim_status = "none";
              else if (!e.claim_status || e.claim_status === "none") e.claim_status = "to_request";
            }
          });
          this.bulkFunder = "";
          this.saySaved(this.plural(n, "toast.updated_one", "toast.updated"));
        },
        bulkSetCat: function () {
          var to = this.cat(this.bulkCat);
          if (!to) return;
          var n = this.patch(this.selIds(), function (e) { if (e.type !== to.type) return false; e.category = to.id; });
          this.bulkCat = "";
          this.saySaved(this.plural(n, "toast.updated_one", "toast.updated"));
        },
        bulkCats: function () {
          // the categories the selection can move to (entries of other types keep theirs)
          var self = this, types = {};
          S.state.entries.forEach(function (e) { if (self.sel[e.id]) types[e.type] = 1; });
          return (this.st().categories || []).filter(function (c) { return types[c.type] && !c.hidden; }).slice().sort(this.byOrder);
        },
        bulkExport: function () {
          var set = this.sel, list = S.state.entries.filter(function (e) { return set[e.id]; });
          this.downloadCsv(list, "selected");
        },

        /* ================= delete, with undo ================= */
        remove: function (ids) {
          var self = this, n = ids.length;
          if (!n) return;
          var msg = n === 1 ? this.t("ask.delete_one", { what: this.entryName(ids[0]) }) : this.t("ask.delete_many", { n: this.count(n) });
          this.confirm(msg, this.t("ask.delete_ok"), true).then(function (yes) {
            if (!yes) return;
            var set = {}, gone = [];
            ids.forEach(function (id) { set[id] = 1; });
            S.state.entries = S.state.entries.filter(function (e) { if (set[e.id]) { gone.push(e); return false; } return true; });
            ids.forEach(function (id) { delete self.sel[id]; });
            self.save();
            self.finishUndo();
            // the photos stay until the undo time is over
            S.undo = { entries: gone, photoIds: gone.filter(function (e) { return e.receipt === "photo"; }).map(function (e) { return e.id; }) };
            self.saySaved(self.plural(n, "toast.deleted_one", "toast.deleted"), true);
            // the row (and its button) is gone: the focus goes to "Undo" — a keyboard or screen reader
            // user can take it back at once (its time stands still while it has the focus)
            self.$nextTick(function () { var b = document.querySelector("[data-xp-undo]"); if (b && S.saveOk !== false) b.focus(); else self.focusView(); });
          });
        },
        // the focus when what had it is gone (a deleted row, a closed toast): the open view's panel
        focusView: function () {
          var p = document.getElementById("xp-panel-" + this.view);
          if (p) p.focus({ preventScroll: true });
        },
        entryName: function (id) {
          var e = S.state.entries.filter(function (x) { return x.id === id; })[0];
          return e ? (e.description || this.catLabel(e.category)) + " · " + this.day(e.date) : "";
        },
        undo: function () {
          var u = S.undo;
          if (!u) return;
          S.undo = null;
          S.state.entries = S.state.entries.concat(u.entries);
          this.save();
          this.saySaved(this.t("toast.restored"));
        },
        // the undo window is over (or a new delete starts one): the photos of deleted entries go
        finishUndo: function () {
          var u = S.undo;
          S.undo = null;
          if (u && u.photoIds.length) u.photoIds.forEach(function (id) { photos.del(id); });
        },

        /* ================= messages ================= */
        // A short message at the bottom of the screen (role=status); with undo it stays 10 seconds —
        // and longer while it has the keyboard focus or the mouse (toastHold), so there is time to use it.
        say: function (msg, withUndo) {
          this.toastMsg = msg;
          this.toastUndo = !!withUndo;
          S.toastHeld = false;
          this.toastTimer(withUndo ? UNDO_MS : 5000);
        },
        toastTimer: function (ms) {
          var self = this;
          clearTimeout(S.toastT);
          S.toastEnd = Date.now() + ms;
          S.toastT = setTimeout(function () { self.toastGone(false); }, ms);
        },
        // focus / mouse in the toast: the time stands still; out again: at least 3 more seconds
        toastHold: function (on) {
          if (!this.toastMsg || S.toastHeld === on) return;
          S.toastHeld = on;
          if (on) { clearTimeout(S.toastT); S.toastLeft = Math.max(0, S.toastEnd - Date.now()); }
          else this.toastTimer(Math.max(3000, S.toastLeft || 0));
        },
        // the toast closes (time over, ×, Undo): its focus goes back to the view
        toastGone: function (undo) {
          var el = document.querySelector(".xp-toast"), had = !!(el && el.contains(document.activeElement));
          clearTimeout(S.toastT);
          S.toastHeld = false;
          if (this.toastUndo && !undo) this.finishUndo();
          this.toastMsg = ""; this.toastUndo = false;
          if (undo) this.undo();
          if (had) this.focusView();
        },
        closeToast: function () { this.toastGone(false); },
        undoToast: function () { this.toastGone(true); },
        flash: function (id) {
          var self = this;
          this.flashId = id;
          clearTimeout(S.flashT);
          S.flashT = setTimeout(function () { self.flashId = ""; }, 2600);
        },
        // The page's own "Are you sure?" (a modal <dialog>): resolves true / false.
        confirm: function (msg, ok, danger) {
          var self = this;
          return new Promise(function (res) {
            if (S.askResolve) S.askResolve(false);
            S.askResolve = res;
            self.ask = { msg: msg, ok: ok || self.t("ask.ok"), danger: !!danger };
            var d = self.$refs.ask;
            if (!d || !d.showModal) { res(window.confirm(msg)); S.askResolve = null; return; }
            S.askBack = document.activeElement;
            d.showModal();
            self.$nextTick(function () { var b = d.querySelector("[data-ask-no]"); if (b) b.focus(); });
          });
        },
        askDone: function (v) {
          var d = this.$refs.ask, r = S.askResolve;
          S.askResolve = null;
          if (d && d.open) d.close();
          if (S.askBack && S.askBack.focus && document.contains(S.askBack)) S.askBack.focus();
          if (r) r(!!v);
        },

        /* ================= suggestions from history (datalists) ================= */
        suggest: function (field) {
          return this.memo("sug:" + field, "", function () {
            var count = {}, last = {};
            S.state.entries.forEach(function (e) {
              var vals = field === "place" ? [e.place, e.from, e.to] : field === "tags" ? (e.tags || []) : [e[field]];
              vals.forEach(function (v) { var s = clean(v); if (!s) return; count[s] = (count[s] || 0) + 1; if (!last[s] || e.date > last[s]) last[s] = e.date || ""; });
            });
            var list = Object.keys(count).sort(function (a, b) { return (last[b] || "").localeCompare(last[a] || "") || count[b] - count[a]; });
            if (field === "event") list = list.concat(S.siteEvents);
            if (field === "place") list = (this.st().places || []).concat(list);
            return uniq(list).slice(0, 60);
          }) || [];
        },
        usedTags: function () { return this.suggest("tags").slice().sort(); },
        usedEvents: function () {
          return this.memo("usedEvents", "", function () {
            return uniq(S.state.entries.map(function (e) { return e.event; })).sort();
          }) || [];
        },

        /* ================= the add / edit dialog ================= */
        // Step 1 asks what is being recorded (big buttons); step 2 shows the fields of the category's
        // template. The form holds what was typed (money and numbers as text); buildEntry() turns it
        // into an entry, GVX normalizes and checks it.
        openAdd: function (type, catId) {
          S.opener = document.activeElement;
          S.formOrig = null;
          this.formMode = "add";
          this.clearPhoto();
          if (type) { this.form = this.blankForm(type, catId); this.formStep = 2; }
          else { this.form = this.blankForm("expense"); this.formStep = 1; }
          this.showForm();
        },
        chooseType: function (type) {
          this.form = this.blankForm(type);
          this.formStep = 2;
          S.formSnap = JSON.stringify(this.form);
          this.focusForm();
        },
        backToTypes: function () { this.formStep = 1; this.formErr = {}; this.formErrs = []; this.focusForm(); },
        openEdit: function (id) {
          var e = S.state.entries.filter(function (x) { return x.id === id; })[0];
          if (!e) return;
          S.opener = document.activeElement;
          this.formMode = "edit";
          this.clearPhoto();
          this.form = this.entryToForm(e);
          // what the entry said when the form opened (buildEntry keeps a request status the form
          // does not show; saveForm deletes a photo the receipt no longer points to)
          S.formOrig = { repaid: e.repaid || "", receipt: e.receipt || "none" };
          this.formStep = 2;
          this.formMore = !!(e.method && e.method !== (this.st().defaults || {}).method) || !!(e.vendor || e.place || e.notes || (e.tags && e.tags.length) || e.claim_ref || e.claim_date);
          if (e.receipt === "photo") this.loadPhoto(e.id);
          this.showForm();
        },
        // "Duplicate": a new entry like this one, dated today. A subscription's start follows the new
        // date; the odometer readings are left out (a new trip). renew: "Record the renewal" — the new
        // term starts where the old one ends (or today, when it has already ended), so the reminder goes.
        duplicate: function (id, renew) {
          var e = S.state.entries.filter(function (x) { return x.id === id; })[0];
          if (!e) return;
          S.opener = document.activeElement;
          S.formOrig = null;
          this.formMode = "add";
          this.clearPhoto();
          var f = this.entryToForm(e), d = today();
          f.id = ""; f.date = d; f.end_date = ""; f.claim_date = ""; f.claim_ref = ""; f.paid_date = ""; f.example = false; f.created = "";
          f.odometer_start = ""; f.odometer_end = "";
          var end = renew ? S.X.subEnd(e) : "";
          f.sub_start = end && end > d ? end : "";
          if (f.receipt === "photo") f.receipt = "none";
          f.claim_status = this.defaultClaim(f, this.cat(f.category));
          if (f.sub_kind === "helped") { f.repaid = "owed"; f.claim_status = "to_request"; }
          this.form = f;
          this.formStep = 2;
          this.showForm();
          this.say(this.t(renew ? "toast.renewing" : "toast.duplicated"));
        },
        renew: function (id) { this.duplicate(id, true); },
        showForm: function () {
          var self = this;
          this.formErr = {}; this.formErrs = []; this.dlgMsg = "";
          S.formSnap = JSON.stringify(this.form);
          this.$nextTick(function () {
            var d = self.$refs.dlg;
            if (d && !d.open) d.showModal();
            self.focusForm();
          });
        },
        focusForm: function () {
          var self = this;
          this.$nextTick(function () {
            var d = self.$refs.dlg;
            if (!d || (self.formStep === 2 && self.formErrs.length)) return;   // the error summary has the focus
            var el = self.formStep === 1 ? d.querySelector("[data-type-btn]") : null;
            // step 2: the first field that is shown (the category, else the date)
            if (!el) el = Array.prototype.filter.call(d.querySelectorAll("#xp-form input, #xp-form select, #xp-form textarea"), function (x) { return x.offsetParent !== null && !x.disabled; })[0];
            if (el) el.focus();
          });
        },
        dirty: function () { return !!this.form && JSON.stringify(this.form) !== S.formSnap; },
        // Esc, the close button and Cancel: ask first when something was typed.
        tryClose: function () {
          var self = this;
          if (!this.dirty() && !S.photo) return this.closeForm();
          this.confirm(this.t("ask.discard"), this.t("ask.discard_ok"), true).then(function (yes) { if (yes) self.closeForm(); });
        },
        closeForm: function () {
          var d = this.$refs.dlg;
          if (d && d.open) d.close();
        },
        // the dialog's close event (any way it closes)
        formClosed: function () {
          this.form = null;
          this.clearPhoto();
          var back = S.opener;
          S.opener = null;
          if (back && back.focus && document.contains(back) && back.offsetParent !== null) back.focus();
          else { var b = document.querySelector("[data-xp-add]"); if (b) b.focus(); }
        },
        defaultClaim: function (f, c) {
          if (f.type !== "expense" && f.type !== "mileage") return "none";
          if (this.isSelf(f.funder)) return "none";
          return c && c.default_claim ? c.default_claim : "to_request";
        },
        blankForm: function (type, catId) {
          var s = this.st(), d = s.defaults || {}, list = this.cats(type), c = this.cat(catId) || list[0] || {}, r = this.defaultRate();
          var other = this.funders().filter(function (x) { return x.kind !== "self" && x.kind !== "person"; })[0];
          var funder = c.default_funder || d.funder || "me";
          if (type === "received" || type === "stock") funder = other ? other.id : "me";
          if (type === "giveaway") funder = "me";
          var f = {
            id: "", type: type, category: c.id || "", date: today(), end_date: "",
            description: "", amount: "", funder: funder,
            claim_status: "none", claim_date: "", claim_ref: "", paid_date: "",
            method: type === "giveaway" || type === "stock" ? "" : (d.method || "cash"),
            vendor: "", event: "", place: "", person: "", person_name: "", item: "", format: "", quantity: "", unit_cost: "", giveaway: !!c.giveaway_default,
            miles: "", rate_id: r.id || "", rate: str(r.rate), from: "", to: "", round_trip: !!d.round_trip, odometer_start: "", odometer_end: "",
            attendees: "", sub_product: "", sub_term: "12", sub_start: "", sub_kind: c.template === "subscription" ? "gift" : "", repaid: "",
            receipt: "none", receipt_ref: "", tags: "", notes: "", custom: {}, example: false, created: "",
          };
          if (f.sub_kind === "gift") f.funder = "me";
          f.claim_status = this.defaultClaim(f, c);
          return f;
        },
        entryToForm: function (e) {
          var self = this, f = this.blankForm(e.type, e.category);
          Object.keys(f).forEach(function (k) { if (e[k] !== undefined && e[k] !== null && typeof f[k] !== "object") f[k] = typeof f[k] === "boolean" ? !!e[k] : str(e[k]); });
          f.amount = e.type === "mileage" ? "" : cents2str(e.amount_cents);
          f.unit_cost = cents2str(e.unit_cost_cents);
          f.tags = (e.tags || []).join(", ");
          f.custom = clone(e.custom || {});
          // the miles as typed: one way when the round trip doubled them (never with the odometer)
          var odo = e.odometer_start !== "" && e.odometer_start != null && e.odometer_end !== "" && e.odometer_end != null;
          if (e.type === "mileage" && e.round_trip && !odo && e.miles !== "" && e.miles != null) f.miles = str(Math.round(Number(e.miles) / 2 * 10) / 10);
          // the rate kept on the entry: its rate in the list, else "kept" (changing settings never changes old entries)
          var hit = this.rates().filter(function (r) { return String(r.rate) === String(e.rate); })[0];
          f.rate_id = hit ? hit.id : (e.type === "mileage" ? "kept" : f.rate_id);
          f.rate = e.type === "mileage" ? str(e.rate) : f.rate;
          var fu = this.funder(e.funder);
          f.person_name = fu && fu.kind === "person" ? self.lbl(fu.name) : "";
          return f;
        },
        tpl: function () {
          var f = this.form;
          if (!f) return "general";
          if (f.type === "expense") { var c = this.cat(f.category); return c && c.template ? c.template : "general"; }
          return f.type;
        },
        // which extra fields a template shows (the always-there ones are in the page)
        has: function (field) {
          var t = this.tpl(), f = this.form;
          var T = {
            item: ["books", "printing", "giveaway", "stock"], format: ["books", "giveaway", "stock"], quantity: ["books", "printing", "giveaway", "stock"],
            unit_cost: ["books"], giveaway: ["books"], subscription: ["subscription"], lodging: ["lodging"], attendees: ["meal"],
            mileage: ["mileage"], money: ["general", "books", "subscription", "lodging", "meal", "printing", "travel", "received"],
          };
          if (field === "funder") return f.type !== "giveaway" && !(t === "subscription" && f.sub_kind === "helped");
          if (field === "status") return (f.type === "expense" || f.type === "mileage") && !this.isSelf(f.funder) && f.sub_kind !== "helped";
          if (field === "method") return f.type === "expense" || f.type === "mileage" || f.type === "received";
          if (field === "receipt") return f.type !== "giveaway" && f.type !== "stock";
          return (T[field] || []).indexOf(t) !== -1;
        },
        funderLabel: function () {
          var t = this.form ? this.form.type : "";
          return this.t(t === "received" || t === "stock" ? "field.funder_from" : "field.funder");
        },
        customFields: function () {
          var type = this.form ? this.form.type : "";
          return (this.st().custom_fields || []).filter(function (c) { return !c.types || !c.types.length || c.types.indexOf(type) !== -1; });
        },
        // a new category: its defaults (who pays, "for giving away")
        onCat: function () {
          var f = this.form, c = this.cat(f.category);
          if (!c) return;
          if (c.default_funder) f.funder = c.default_funder;
          f.giveaway = !!c.giveaway_default;
          if (c.template === "subscription" && !f.sub_kind) { f.sub_kind = "gift"; f.funder = "me"; }
          if (c.template !== "subscription") f.sub_kind = "";
          f.claim_status = this.defaultClaim(f, c);
        },
        onFunder: function () {
          var f = this.form;
          if (this.isSelf(f.funder)) f.claim_status = "none";
          else if (f.claim_status === "none") f.claim_status = this.defaultClaim(f, this.cat(f.category));
        },
        onSubKind: function () {
          var f = this.form;
          if (f.sub_kind === "gift" || f.sub_kind === "self") { f.funder = "me"; f.repaid = ""; }
          else if (f.sub_kind === "group") { if (this.isSelf(f.funder)) f.funder = this.funder("group") ? "group" : f.funder; f.repaid = ""; }
          else if (f.sub_kind === "helped") { f.repaid = f.repaid || "owed"; if (!f.person_name) f.person_name = f.person; }
          f.claim_status = f.sub_kind === "helped" ? "to_request" : this.defaultClaim(f, this.cat(f.category));
        },
        onRate: function () {
          var f = this.form, r = this.rates().filter(function (x) { return x.id === f.rate_id; })[0];
          if (r) f.rate = str(r.rate);
        },
        rateOptions: function () {
          var list = this.rates().slice();
          if (this.form && this.form.rate_id === "kept") list = [{ id: "kept", name: this.t("form.rate_kept"), rate: this.form.rate }].concat(list);
          return list;
        },
        odo: function () { var f = this.form; return !!f && num(f.odometer_start) !== "" && num(f.odometer_end) !== ""; },
        // the miles that count: the odometer (the whole trip), else the miles × 2 for a round trip
        milesValue: function () {
          var f = this.form;
          if (!f) return 0;
          if (this.odo()) return Math.max(0, Math.round((num(f.odometer_end) - num(f.odometer_start)) * 10) / 10);
          var m = num(f.miles);
          if (m === "") return 0;
          return Math.round(m * (f.round_trip ? 2 : 1) * 10) / 10;
        },
        mileagePreview: function () {
          var f = this.form, m = this.milesValue();
          if (!f || !m || f.rate === "") return "";
          var c = 0;
          try { c = S.X.mileageCents(m, f.rate); } catch (e) { return ""; }
          return this.t("form.mileage_preview", { miles: this.count(m), rate: f.rate, amount: this.money(c) });
        },
        moneyOf: function (s) {
          if (s === "" || s == null) return "";
          var c = null;
          try { c = S.X.parseMoney(String(s)); } catch (e) { c = null; }
          return c == null || isNaN(c) ? null : Math.abs(Math.round(c));
        },
        negative: function (s) { var c = null; try { c = S.X.parseMoney(String(s)); } catch (e) { c = null; } return c != null && c < 0; },
        booksAuto: function () {
          var f = this.form;
          if (!f || !this.has("unit_cost")) return false;
          return num(f.quantity) !== "" && this.moneyOf(f.unit_cost) != null && this.moneyOf(f.unit_cost) !== "";
        },
        booksTotal: function () {
          if (!this.booksAuto()) return "";
          var f = this.form;
          return this.t("form.books_total", { qty: this.count(num(f.quantity)), unit: this.money(this.moneyOf(f.unit_cost)), total: this.money(Math.round(num(f.quantity) * this.moneyOf(f.unit_cost))) });
        },
        nights: function () {
          var f = this.form;
          if (!f || !f.date || !f.end_date) return "";
          var n = Math.round((Date.parse(f.end_date + "T12:00:00Z") - Date.parse(f.date + "T12:00:00Z")) / 864e5);
          return n > 0 ? this.plural(n, "form.nights_one", "form.nights") : "";
        },
        // An existing person (a funder of kind "person") by name, or a new one.
        ensurePerson: function (name) {
          var s = this.st(), n = norm(name);
          if (!n) return "";
          var hit = (s.funders || []).filter(function (f) { return f.kind === "person" && norm(typeof f.name === "string" ? f.name : (f.name.en || f.name.es)) === n; })[0];
          if (hit) return hit.id;
          var id = S.X.newId();
          var max = (s.funders || []).reduce(function (m, f) { return Math.max(m, f.order || 0); }, 0);
          s.funders.push({ id: id, kind: "person", name: clean(name), hidden: false, order: max + 1, builtin: false });
          return id;
        },
        // Money received from a person: the purchases made for them that it covers (GVX.settleRepayments,
        // oldest first) are marked repaid — paid on that day — so they leave the requests. → how many.
        settle: function (funder, date) {
          var X = S.X, st = this.st(), ids = X.settleRepayments(S.state.entries, st, funder) || [], set = {}, now = nowIso();
          if (!ids.length) return 0;
          ids.forEach(function (id) { set[id] = 1; });
          S.state.entries = S.state.entries.map(function (e) {
            if (!set[e.id]) return e;
            var c = clone(e);
            c.repaid = "repaid"; c.claim_status = "paid"; c.paid_date = c.paid_date || date || today(); c.updated = now;
            var r = X.normalizeEntry(c, st);
            return r && r.entry ? r.entry : c;
          });
          return ids.length;
        },
        buildEntry: function () {
          var f = this.form, t = f.type, tp = this.tpl(), errs = [];
          var e = {
            id: f.id, type: t, date: f.date, end_date: this.has("lodging") ? f.end_date : "", category: f.category,
            description: clean(f.description), funder: f.funder, claim_status: f.claim_status,
            claim_date: f.claim_date, claim_ref: clean(f.claim_ref), paid_date: f.paid_date,
            method: this.has("method") ? f.method : "", vendor: clean(f.vendor), event: clean(f.event), place: clean(f.place),
            person: this.has("subscription") ? clean(f.person_name || f.person) : clean(f.person), item: this.has("item") ? clean(f.item) : "",
            format: this.has("format") ? f.format : "", quantity: this.has("quantity") ? num(f.quantity) : "",
            unit_cost_cents: "", giveaway: this.has("giveaway") ? !!f.giveaway : false,
            miles: "", rate: "", from: "", to: "", round_trip: false, odometer_start: "", odometer_end: "",
            nights: "", attendees: this.has("attendees") ? num(f.attendees) : "",
            sub_product: "", sub_term: "", sub_start: "", sub_kind: "", repaid: "",
            receipt: this.has("receipt") ? f.receipt : "none", receipt_ref: f.receipt === "file" ? clean(f.receipt_ref) : clean(f.receipt_ref),
            tags: uniq(String(f.tags || "").split(/[,;]/)), notes: String(f.notes || "").trim(), custom: clone(f.custom || {}),
            example: !!f.example, created: f.created || "", amount_cents: 0,
          };
          if (this.has("money")) {
            var auto = this.booksAuto(), c = auto ? Math.round(num(f.quantity) * this.moneyOf(f.unit_cost)) : this.moneyOf(f.amount);
            // the amount is required: left empty it is an error (a typed 0 is fine); a minus sign is
            // not a way to record money coming in (that is "Money received")
            if (!auto && clean(f.amount) === "") errs.push({ field: "amount", text: this.t("form.err_amount_required") });
            else if (c === null) errs.push({ field: "amount", text: this.t("form.err_money") });
            else if (!auto && this.negative(f.amount)) errs.push({ field: "amount", text: this.t("form.err_amount_negative") });
            e.amount_cents = c === null || c === "" ? "" : c;
          }
          if (this.has("unit_cost")) {
            var u = this.moneyOf(f.unit_cost);
            if (u === null) errs.push({ field: "unit_cost", text: this.t("form.err_money") });
            e.unit_cost_cents = u === null ? "" : u;
          }
          if (tp === "mileage") {
            e.from = clean(f.from); e.to = clean(f.to); e.round_trip = !!f.round_trip && !this.odo();
            e.odometer_start = num(f.odometer_start); e.odometer_end = num(f.odometer_end);
            e.miles = this.milesValue() || num(f.miles);
            e.rate = str(f.rate);
            if (e.odometer_start !== "" && e.odometer_end !== "" && e.odometer_end < e.odometer_start) errs.push({ field: "odometer_end", text: this.t("form.err_odometer") });
          }
          if (tp === "subscription") {
            e.sub_product = f.sub_product; e.sub_term = num(f.sub_term); e.sub_start = f.sub_start || f.date; e.sub_kind = f.sub_kind;
            if (f.sub_kind === "helped") {
              if (!clean(f.person_name)) errs.push({ field: "person_name", text: this.t("form.err_person") });
              else { e.funder = this.ensurePerson(f.person_name); e.person = clean(f.person_name); }
              e.repaid = f.repaid || "owed";
              // the request status follows the pay-back when the pay-back is chosen here: still owed →
              // to ask for; paid back → paid (it leaves the requests and the list says so); forgiven →
              // nothing to ask (a gift). An edit that leaves the pay-back alone keeps the status the
              // entry has (a request marked submitted stays submitted: the form does not show it).
              var o = S.formOrig, kept = this.formMode === "edit" && !!o && o.repaid === e.repaid;
              if (!kept) e.claim_status = e.repaid === "repaid" ? "paid" : e.repaid === "forgiven" ? "none" : "to_request";
              else if (e.repaid === "owed" && f.claim_status === "paid") e.repaid = "repaid";          // marked paid earlier: paid back
              else if (e.repaid === "owed" && f.claim_status === "none") e.claim_status = "to_request";
              if (e.repaid === "repaid" && !e.paid_date) e.paid_date = today();
            }
          }
          if (t === "giveaway") { e.funder = "me"; e.amount_cents = 0; e.claim_status = "none"; }
          if (t === "received" || t === "stock") e.claim_status = "none";
          if (t === "stock") e.amount_cents = 0;
          if (this.isSelf(e.funder) && e.sub_kind !== "helped") e.claim_status = "none";
          if (S.photo === "remove" && e.receipt === "photo") e.receipt = "none";
          return { entry: e, errs: errs };
        },
        saveForm: function (again) {
          var self = this, X = S.X, st = this.st(), nFunders = (st.funders || []).length, b = this.buildEntry();
          var r = X.normalizeEntry(b.entry, st) || { entry: b.entry };
          var e = r.entry || b.entry;
          var errs = b.errs.slice();
          (X.validateEntry(e, st) || []).forEach(function (v) {
            if (!errs.some(function (x) { return x.field === v.field; })) errs.push({ field: v.field, text: self.msgKey(v.key) });
          });
          this.formErr = {};
          errs.forEach(function (x) { self.formErr[x.field] = x.text; });
          this.formErrs = errs;
          if (errs.length) {
            // nothing is saved: a person the form just added ("Helped them buy it") goes away again
            if (st.funders && st.funders.length > nFunders) st.funders.length = nFunders;
            this.$nextTick(function () { focusShown(document.getElementById("xp-form-errors")); });
            return;
          }
          var now = nowIso(), isNew = !e.id || !S.state.entries.some(function (x) { return x.id === e.id; });
          if (!e.id) e.id = X.newId();
          if (isNew && !e.created) e.created = now;
          e.updated = now;
          if (isNew) S.state.entries.push(e);
          else S.state.entries = S.state.entries.map(function (x) { return x.id === e.id ? e : x; });
          var first = S.state.entries.length === 1;
          // the photo: stored on this device under the entry's id (or removed — also when the receipt
          // is now kept some other way: a photo nothing points to never stays behind)
          if (S.photo && S.photo !== "remove" && e.receipt === "photo") {
            var p = S.photo;
            photos.put({ id: e.id, type: "image/jpeg", blob: p.blob, w: p.w, h: p.h, name: p.name || "", added: now })
              .catch(function () { self.say(self.t("toast.photo_failed")); });
          } else if (S.photo === "remove" || (S.formOrig && S.formOrig.receipt === "photo" && e.receipt !== "photo")) photos.del(e.id);
          S.photo = null;
          // money a person paid back settles what was bought for them (oldest first)
          var settled = e.type === "received" ? this.settle(e.funder, e.date) : 0;
          var stored = this.save();
          if (stored) this.askPersist();
          this.flash(e.id);
          var msg = first ? this.t("toast.saved_first") : this.t("toast.saved");
          if (settled) msg += " · " + this.plural(settled, "toast.settled_one", "toast.settled");
          this.saySaved(msg);
          if (again) {
            var keep = this.form, nf = this.blankForm(keep.type, keep.category);
            ["date", "funder", "claim_status", "method", "event", "place", "rate_id", "rate", "round_trip", "from", "sub_kind", "format"].forEach(function (k) { nf[k] = keep[k]; });
            this.form = nf;
            this.formMode = "add";
            this.clearPhoto();
            S.formSnap = JSON.stringify(nf);
            this.formErr = {}; this.formErrs = [];
            this.dlgMsg = "";
            this.$nextTick(function () { self.dlgMsg = self.t("form.saved_next"); });
            this.focusForm();
          } else {
            this.closeForm();
          }
        },
        errFocus: function (field) {
          field = field === "amount_cents" ? "amount" : field === "type" ? "category" : String(field).replace(/^custom:/, "cf-");
          var el = document.getElementById("xp-f-" + field);
          if (!el) { this.formMore = true; var self = this; this.$nextTick(function () { var x = document.getElementById("xp-f-" + field); if (x) x.focus(); }); return; }
          el.focus();
        },
        errText: function (field) { return this.formErr[field] || ""; },

        /* ---- the receipt photo in the form ---- */
        clearPhoto: function () {
          if (S.photoUrl) { try { URL.revokeObjectURL(S.photoUrl); } catch (e) { /* gone */ } }
          S.photoUrl = ""; S.photo = null;
          this.photoUrl = ""; this.photoBusy = false;
        },
        loadPhoto: function (id) {
          var self = this;
          photos.get(id).then(function (rec) {
            if (!rec || !rec.blob || !self.form || self.form.id !== id) return;
            S.photoUrl = URL.createObjectURL(rec.blob);
            self.photoUrl = S.photoUrl;
          });
        },
        onPhoto: function (ev) {
          var self = this, file = ev.target.files && ev.target.files[0];
          ev.target.value = "";
          if (!file) return;
          this.photoBusy = true;
          shrinkPhoto(file).then(function (p) {
            if (S.photoUrl) URL.revokeObjectURL(S.photoUrl);
            p.name = file.name;
            S.photo = p;
            S.photoUrl = URL.createObjectURL(p.blob);
            self.photoUrl = S.photoUrl;
            self.form.receipt = "photo";
            self.photoBusy = false;
            GV.announce && GV.announce(self.t("form.photo_added"));
          }, function () { self.photoBusy = false; self.say(self.t("toast.photo_failed")); });
        },
        removePhoto: function () {
          if (S.photoUrl) URL.revokeObjectURL(S.photoUrl);
          S.photoUrl = ""; this.photoUrl = "";
          S.photo = "remove";
          this.form.receipt = "none";
          GV.announce && GV.announce(this.t("form.photo_removed"));
        },

        /* ================= Summary ================= */
        sum: function () {
          var r = this.range();
          return this.memo("sum", r.from + "|" + r.to, function () { return S.X.summary(S.state.entries, this.st(), { from: r.from, to: r.to }); }) || {};
        },
        stats: function () {
          var s = this.sum(), n = this.inPeriodCount();
          return [
            { id: "spent", icon: "receipt", tone: "xp-tone-gv", label: this.t("sum.spent"), value: this.money(s.spent_cents), note: this.plural(n, "list.entries_one", "list.entries") },
            { id: "self", icon: "hand-heart", tone: "xp-tone-vine", label: this.t("sum.self"), value: this.money(s.self_cents), note: this.t("sum.self_note") },
            { id: "owed", icon: "clock", tone: "xp-tone-lv", label: this.t("sum.owed"), value: this.money(s.owed_cents), note: this.t("sum.claimable", { amount: this.money(s.claimable_cents) }) },
            { id: "received", icon: "banknote", tone: "xp-tone-teal", label: this.t("sum.received"), value: this.money(s.received_cents), note: this.t("sum.received_note") },
            { id: "miles", icon: "car", tone: "xp-tone-grape", label: this.t("sum.miles"), value: this.t("sum.miles_value", { n: this.count(s.miles || 0) }), note: this.t("sum.miles_note", { amount: this.money(s.mileage_cents) }) },
            { id: "given", icon: "heart-handshake", tone: "xp-tone-rose", label: this.t("sum.given"), value: this.count(s.items_given || 0), note: this.t("sum.on_hand", { n: this.count(s.items_on_hand || 0) }) },
          ];
        },
        byCat: function () {
          var self = this, s = this.sum(), list = (s.by_category || []).filter(function (x) { return x.cents > 0; });
          var total = list.reduce(function (a, x) { return a + x.cents; }, 0) || 1;
          var max = list.reduce(function (a, x) { return Math.max(a, x.cents); }, 0) || 1;
          return list.slice().sort(function (a, b) { return b.cents - a.cents; }).map(function (x) {
            var pct = Math.round(x.cents / total * 100);
            return { id: x.id, label: self.catLabel(x.id), icon: self.catIcon(x.id), tone: self.catTone(x.id), amount: self.money(x.cents), share: self.t("sum.share", { n: pct }), w: Math.max(2, Math.round(x.cents / max * 100)), n: x.count };
          });
        },
        monthName: function (ym) {
          var s = GV.fmtDate ? GV.fmtDate(ym + "-15T12:00:00Z", { month: "short", year: "numeric" }) : ym;
          return s || ym;
        },
        byMonth: function () {
          var self = this, list = (this.sum().by_month || []).slice().sort(function (a, b) { return a.ym < b.ym ? -1 : 1; });
          var max = list.reduce(function (a, x) { return Math.max(a, x.spent || 0, x.received || 0); }, 0) || 1;
          return list.map(function (x) {
            return { ym: x.ym, label: self.monthName(x.ym), spent: self.money(x.spent), received: self.money(x.received),
                     ws: (x.spent ? Math.max(2, Math.round(x.spent / max * 100)) : 0), wr: (x.received ? Math.max(2, Math.round(x.received / max * 100)) : 0) };
          });
        },
        balances: function () {
          var self = this, r = this.range();
          return this.memo("bal", r.from + "|" + r.to, function () {
            return (S.X.funderBalances(S.state.entries, this.st(), { from: r.from, to: r.to }) || []).filter(function (b) {
              return !self.isSelf(b.funder) && (b.claimed_cents || b.received_cents);
            }).map(function (b) {
              return { id: b.funder, name: self.funderName(b.funder), person: (self.funder(b.funder) || {}).kind === "person",
                       claimed: self.money(b.claimed_cents), toRequest: self.money(b.to_request_cents), submitted: self.money(b.submitted_cents),
                       paid: self.money(b.paid_cents), received: self.money(b.received_cents), balance: b.balance_cents,
                       balanceText: b.balance_cents < 0 ? self.t("sum.they_owe", { amount: self.money(-b.balance_cents) }) : b.balance_cents > 0 ? self.t("sum.you_hold", { amount: self.money(b.balance_cents) }) : self.t("sum.even") };
            }).concat((S.X.peopleOwed(S.state.entries, this.st(), { from: r.from, to: r.to }) || []).filter(function (p) { return !p.funder && p.owed_cents > 0; }).map(function (p, i) {
              return { id: "person:" + i, name: p.person, person: true, claimed: self.money(p.claimed_cents), toRequest: self.money(p.owed_cents), submitted: self.money(0),
                       paid: self.money(p.settled_cents), received: self.money(p.received_cents), balance: -p.owed_cents, balanceText: self.t("sum.they_owe", { amount: self.money(p.owed_cents) }) };
            }));
          }) || [];
        },
        peopleOwed: function () {
          var self = this;
          return this.memo("people", "", function () {
            return (S.X.peopleOwed(S.state.entries, this.st()) || []).filter(function (p) { return p.owed_cents > 0; }).map(function (p) {
              var id = p.funder || p.person || "";
              return { id: id, name: self.funder(id) ? self.funderName(id) : (p.person || id), owed: self.money(p.owed_cents), n: (p.entries || []).length };
            });
          }) || [];
        },
        budgetRows: function () {
          var self = this;
          return this.memo("budgets", "", function () {
            return (S.X.budgets(S.state.entries, this.st(), today()) || []).map(function (b) {
              var bu = b.budget || {}, pct = b.pct == null ? 0 : Math.max(0, Math.round(b.pct));
              return { id: bu.id, label: bu.label || self.funderName(bu.funder), funder: self.funderName(bu.funder), year: bu.year || "",
                       used: self.money(b.used_cents), left: self.money(Math.abs(b.left_cents)), total: self.money(bu.amount_cents), pct: pct, over: !!b.over };
            });
          }) || [];
        },
        renewalRows: function () {
          var self = this, days = this.st().renewal_days || 60;
          return this.memo("renew", "", function () {
            return (S.X.renewals(S.state.entries, today(), days) || []).map(function (r) {
              var e = r.entry, end = r.sub_end;
              return { id: e.id, what: self.t("sub_product." + (e.sub_product || "other")), who: e.person || "", end: self.day(end, true), past: r.days_left < 0 };
            });
          }) || [];
        },
        staleRows: function () {
          var self = this;
          return this.memo("stale", "", function () {
            return (S.X.staleClaims(S.state.entries, today(), 30) || []).map(function (r) {
              var e = r.entry;
              return { id: e.id, desc: e.description || self.catLabel(e.category), funder: self.funderName(e.funder), since: self.day(e.claim_date, true), amount: self.money(e.amount_cents) };
            });
          }) || [];
        },
        backupDue: function () {
          this.rev;
          var m = (S.state && S.state.meta) || {}, days = this.st().backup_reminder_days || 30;
          if (!S.state || !S.state.entries.length) return false;
          var d = daysSince(m.lastBackup);
          return d === null || d > days;
        },
        // what the Reminders card lists (and the Summary tab's badge counts): requests waiting too long and
        // the backup — renewals have their own card (Subscriptions)
        reminderCount: function () { return this.staleRows().length + (this.backupDue() ? 1 : 0); },

        /* ================= Giveaways ================= */
        inv: function () {
          var self = this;
          return this.memo("inv", "", function () {
            var r = S.X.inventory(S.state.entries) || [];
            var list = Array.isArray(r) ? r : Object.keys(r).map(function (k) { return r[k]; });
            return list.map(function (x) {
              return { key: norm(x.item) + "|" + (x.format || ""), item: x.item || self.t("give.no_item"), format: x.format || "", formatText: x.format ? self.t("format." + x.format) : "",
                       bought: self.count(x.bought_qty || 0), received: self.count(x.received_qty || 0), given: self.count(x.given_qty || 0),
                       onHand: x.on_hand || 0, onHandText: self.count(x.on_hand || 0), avg: x.avg_unit_cents ? self.money(x.avg_unit_cents) : "—",
                       hasAvg: !!x.avg_unit_cents, cost: self.money(x.cost_cents || 0) };
            }).sort(function (a, b) { return a.item.localeCompare(b.item); });
          }) || [];
        },
        giveEvents: function (year) {
          var self = this;
          return this.memo("giveEv", String(year || ""), function () {
            var range = year ? { from: year + "-01-01", to: year + "-12-31" } : {};
            return (S.X.eventGiveaways(S.state.entries, range) || []).map(function (g, i) {
              return { key: (norm(g.event) || "-") + i, name: g.event || self.t("give.no_event"), date: self.day(g.last_date, true), total: self.count(g.total_qty),
                       items: (g.items || []).map(function (it, j) { return { key: j + "|" + it.item, text: self.itemText(it.item, it.format), qty: self.count(it.qty) }; }) };
            });
          }) || [];
        },
        itemText: function (item, format) {
          var name = item || this.t("give.no_item"), f = format ? this.t("format." + format) : "";
          return f && norm(name).indexOf(norm(f)) === -1 ? name + " (" + f + ")" : name;
        },
        invNegative: function () { return this.inv().some(function (x) { return x.onHand < 0; }); },
        itemSuggest: function () { return uniq(this.inv().map(function (x) { return x.item; }).concat(this.suggest("item"))); },

        /* ================= Requests (reimbursement) ================= */
        rqRange: function () { return periodRange(this.rq.period, this.panels(), this.rq.from, this.rq.to); },
        rqStatuses: function () { var st = this.rq.st; return CLAIMS.filter(function (k) { return st[k]; }); },
        rqKey: function () { var r = this.rqRange(); return [this.rq.funder, r.from, r.to, this.rqStatuses().join(","), this.rq.names, this.L].join("|"); },
        // the entries the request lists (the core's own selection: claimLines().ids)
        rqEntries: function () {
          return this.memo("rqE", this.rqKey(), function () {
            var c = this.rqClaim(), ids = {};
            if (!c) return [];
            (c.ids || []).forEach(function (id) { ids[id] = 1; });
            return S.state.entries.filter(function (e) { return ids[e.id]; });
          }) || [];
        },
        rqClaim: function () {
          var self = this;
          return this.memo("rqC", this.rqKey(), function () {
            var r = this.rqRange();
            if (!this.rq.funder) return null;
            return S.X.claimLines(S.state.entries, this.st(), { funder: this.rq.funder, from: r.from, to: r.to, statuses: this.rqStatuses(), includeNames: !!this.rq.names, lang: this.L, strings: S.ui });
          });
        },
        // the "Expenses" table: every line except the miles, which have their own log below (each
        // claimed item appears once on the printed request; the totals count both tables)
        rqLines: function () {
          var self = this, c = this.rqClaim(), miles = {};
          ((c && c.mileage) || []).forEach(function (m) { miles[m.id] = 1; });
          return ((c && c.lines) || []).filter(function (l) { return !miles[l.id]; }).map(function (l, i) {
            var k = l.receipt_kind || "none";
            return { i: i, date: self.day(l.date, "mid"), desc: l.description || "", cat: l.category || "", amount: self.money(l.amount_cents),
                     receipt: self.t("req.receipt_" + (["photo", "paper", "file"].indexOf(k) !== -1 ? k : "none")), hasReceipt: !!l.receipt };
          });
        },
        rqMileage: function () {
          var self = this, c = this.rqClaim();
          return ((c && c.mileage) || []).map(function (l, i) {
            return { i: i, date: self.day(l.date, "mid"), route: clean(l.from) + (l.to ? " → " + clean(l.to) : ""), purpose: l.description || l.purpose || "",
                     miles: self.count(l.miles || 0), rate: "$" + str(l.rate), amount: self.money(l.amount_cents) };
          });
        },
        rqTotals: function () {
          var self = this, c = this.rqClaim(), t = (c && c.totals) || {};
          var cats = t.by_category || [];
          if (!Array.isArray(cats)) cats = Object.keys(cats).map(function (k) { return { id: k, cents: cats[k] }; });
          return { total: this.money(t.cents || 0), miles: this.count(t.miles || 0), cents: t.cents || 0,
                   cats: cats.map(function (x) { return { id: x.id, label: x.label || self.catLabel(x.id), amount: self.money(x.cents) }; }) };
        },
        // the funder with the most still to request (else the first one with anything asked of it)
        rqBestFunder: function () {
          var self = this, best = null;
          (S.X.funderBalances(S.state.entries, this.st(), {}) || []).forEach(function (b) {
            if (self.isSelf(b.funder) || !self.funder(b.funder)) return;
            if (!best || b.to_request_cents > best.to_request_cents || (!best.to_request_cents && b.claimed_cents > best.claimed_cents)) best = b;
          });
          return best && (best.to_request_cents || best.claimed_cents) ? best.funder : "";
        },
        rqRefDefault: function () {
          var p = this.st().profile || {}, d = clean(p.district).replace(/^(district|distrito)\s*/i, "");
          var ym = today().slice(0, 7);
          return (d ? "D" + d + "-" : "") + ym;
        },
        rqPeriodText: function () {
          var r = this.rqRange();
          if (!r.from && !r.to) return this.t("req.all_dates");
          return this.t("req.dates", { from: r.from ? this.day(r.from, true) : "…", to: r.to ? this.day(r.to, true) : "…" });
        },
        rqStart: function (funderId) {
          this.rq.funder = funderId;
          this.rq.st = { to_request: true, submitted: false, paid: false, denied: false };
          this.go("requests");
          this.$nextTick(function () { var el = document.getElementById("xp-rq-funder"); if (el) el.focus(); });
        },
        rqText: function () {
          var c = this.rqClaim();
          if (!c) return "";
          try { return S.X.claimText(c, S.ui, this.L); } catch (e) { return ""; }
        },
        rqCopy: function () {
          var self = this, text = this.rqText();
          if (!text) return;
          writeText(text).then(function () { self.say(self.t("toast.copied")); }, function () { self.say(self.t("toast.copy_failed")); });
        },
        rqShare: function () {
          var self = this, text = this.rqText();
          if (!text) return;
          if (navigator.share) {
            navigator.share({ title: this.t("req.doc_title"), text: text }).catch(function (e) { if (!e || e.name !== "AbortError") self.rqCopy(); });
            return;
          }
          this.rqCopy();
        },
        // "Download CSV": the request's own lines (GVX.claimCSV) — what the printed request says, names
        // left out unless the request includes them; never the full record (that is Settings → Data)
        rqCsv: function () {
          var c = this.rqClaim();
          if (!c || !(c.lines || []).length) { this.say(this.t("toast.nothing_to_export")); return; }
          var name = this.t("data.file_base") + "-request-" + (safeName(this.funderName(this.rq.funder)) || "funder") + "-" + today() + ".csv";
          saveBlob(new Blob([S.X.claimCSV(c, S.ui, this.L)], { type: "text/csv;charset=utf-8" }), name);
          this.say(this.t("toast.downloaded", { file: name }));
        },
        rqMark: function () {
          var self = this, ids = this.rqEntries().filter(function (e) { return e.claim_status === "to_request" || e.claim_status === "denied"; }).map(function (e) { return e.id; });
          if (!ids.length) return;
          var ref = clean(this.rq.ref) || this.rqRefDefault(), d = today();
          this.confirm(this.t("ask.mark_submitted", { n: this.count(ids.length), ref: ref }), this.t("req.mark_ok")).then(function (yes) {
            if (!yes) return;
            var n = self.patch(ids, function (e) { e.claim_status = "submitted"; e.claim_date = d; e.claim_ref = ref; });
            self.rq.st.submitted = true;
            self.saySaved(self.plural(n, "toast.submitted_one", "toast.submitted"));
          });
        },
        rqToMark: function () { return this.rqEntries().filter(function (e) { return e.claim_status === "to_request" || e.claim_status === "denied"; }).length; },
        // the receipts appendix: the photos kept on this device, one per half page
        rqLoadPhotos: function () {
          var self = this;
          S.rqUrls.forEach(function (u) { try { URL.revokeObjectURL(u); } catch (e) { /* gone */ } });
          S.rqUrls = [];
          this.rqPhotos = [];
          if (!this.rq.photos) return Promise.resolve();
          // each caption says what the request's line says (no name, unless the request includes names)
          var lines = {};
          ((this.rqClaim() || {}).lines || []).forEach(function (l) { lines[l.id] = l; });
          var list = this.rqEntries().filter(function (e) { return e.receipt === "photo" && lines[e.id]; });
          return Promise.all(list.map(function (e) { return photos.get(e.id).then(function (rec) { return { e: e, rec: rec }; }); })).then(function (all) {
            self.rqPhotos = all.filter(function (x) { return x.rec && x.rec.blob; }).map(function (x) {
              var u = URL.createObjectURL(x.rec.blob), l = lines[x.e.id];
              S.rqUrls.push(u);
              return { id: x.e.id, url: u, label: self.day(l.date, true) + " · " + l.description + " · " + self.money(l.amount_cents) };
            });
          });
        },
        rqPrint: function () {
          var self = this;
          this.rqLoadPhotos().then(function () { self.printPart("request", self.t("req.doc_title") + " — " + self.funderName(self.rq.funder)); });
        },
        printPart: function (kind, title) {
          var root = document.documentElement, was = document.title;
          root.setAttribute("data-xp-print", kind);
          document.title = title;   // the file name "Save as PDF" suggests
          var done = function () { root.removeAttribute("data-xp-print"); document.title = was; window.removeEventListener("afterprint", done); };
          window.addEventListener("afterprint", done);
          this.$nextTick(function () { setTimeout(function () { window.print(); if (!("onafterprint" in window)) done(); }, 60); });
        },
        profileLine: function () {
          var p = this.st().profile || {};
          return [clean(p.name), clean(p.position), clean(p.district)].filter(Boolean).join(" · ");
        },
        todayLong: function () { return this.day(today(), true); },

        /* ---- the year summary (for your records or the committee's report) ---- */
        years: function () {
          this.rev;
          var ys = {}, y = new Date().getFullYear();
          ys[y] = 1;
          S.state.entries.forEach(function (e) { var k = String(e.date || "").slice(0, 4); if (/^\d{4}$/.test(k)) ys[k] = 1; });
          return Object.keys(ys).map(Number).sort(function (a, b) { return b - a; });
        },
        yearData: function () {
          var self = this, y = String(this.yr);
          return this.memo("year", y + "|" + this.L, function () {
            var s = S.X.summary(S.state.entries, this.st(), { from: y + "-01-01", to: y + "-12-31" }) || {};
            var subs = { gift: 0, helped: 0, group: 0, self: 0 };
            S.state.entries.forEach(function (e) { if (String(e.date).slice(0, 4) === y && e.sub_kind && subs[e.sub_kind] !== undefined) subs[e.sub_kind]++; });
            var cats = (s.by_category || []).filter(function (x) { return x.cents > 0; }).sort(function (a, b) { return b.cents - a.cents; })
              .map(function (x) { return { id: x.id, label: self.catLabel(x.id), amount: self.money(x.cents), n: x.count }; });
            var months = (s.by_month || []).slice().sort(function (a, b) { return a.ym < b.ym ? -1 : 1; })
              .map(function (x) { return { ym: x.ym, label: self.monthName(x.ym), spent: self.money(x.spent), received: self.money(x.received) }; });
            return { spent: self.money(s.spent_cents), self: self.money(s.self_cents), received: self.money(s.received_cents), owed: self.money(s.owed_cents),
                     miles: self.count(s.miles || 0), mileage: self.money(s.mileage_cents), given: self.count(s.items_given || 0),
                     cats: cats, months: months, subs: subs, events: this.giveEvents(y) };
          }) || { cats: [], months: [], subs: {}, events: [] };
        },
        yearPrint: function () { this.printPart("year", this.t("year.doc_title", { year: this.yr })); },

        /* ================= export ================= */
        stamp: function (field) { S.state.meta = S.state.meta || {}; S.state.meta[field] = nowIso(); },
        downloadCsv: function (list, what) {
          if (!list.length) { this.say(this.t("toast.nothing_to_export")); return; }
          var csv = S.X.toCSV(list, this.st(), { lang: this.L }) || "";
          if (csv.charCodeAt(0) !== 0xfeff) csv = "﻿" + csv;
          var name = this.t("data.file_base") + "-" + (what && what !== "all" ? what + "-" : "") + today() + ".csv";
          saveBlob(new Blob([csv], { type: "text/csv;charset=utf-8" }), name);
          // a CSV is an export, not a backup: it has no photos and no settings ("Last backup" and its
          // reminder wait for the full backup)
          this.stamp("lastExport");
          this.save();
          this.say(this.t("toast.downloaded", { file: name }));
        },
        exportAll: function () { this.downloadCsv(S.state.entries.slice(), "all"); },
        // The full backup: entries, settings and the receipt photos of the entries, in one .json file.
        exportBackup: function () {
          var self = this;
          if (!S.state.entries.length) { this.say(this.t("toast.nothing_to_export")); return; }
          this.say(this.t("toast.preparing"));
          var mine = this.photoIds();
          photos.all().then(function (recs) {
            return Promise.all((recs || []).filter(function (r) { return r && mine[r.id]; }).map(function (r) {
              return r && r.blob ? blobToDataUrl(r.blob).then(function (u) { return { id: r.id, type: r.type || "image/jpeg", dataUrl: u }; }) : null;
            }));
          }).then(function (receipts) {
            var b = S.X.toBackup(S.state, (receipts || []).filter(function (x) { return x && x.dataUrl; }));
            var text = typeof b === "string" ? b : JSON.stringify(b);
            var name = self.t("data.file_base") + "-" + self.t("data.backup_word") + "-" + today() + ".json";
            saveBlob(new Blob([text], { type: "application/json" }), name);
            self.stamp("lastBackup");
            self.save();
            self.say(self.t("toast.downloaded", { file: name }));
          }).catch(function (e) { if (window.console) console.error("[expenses]", e); self.say(self.t("toast.backup_failed")); });
        },
        // the entries that have a photo (and the ones a pending "Undo" would bring back)
        photoIds: function () {
          var ids = {};
          S.state.entries.forEach(function (e) { if (e.receipt === "photo") ids[e.id] = 1; });
          if (S.undo) S.undo.photoIds.forEach(function (id) { ids[id] = 1; });
          return ids;
        },
        // Photos no entry points to any more are deleted: a delete whose undo time never ran out (the
        // page was closed), a CSV import that replaced everything. A deleted receipt never travels on
        // in a backup.
        cleanPhotos: function () {
          var mine = this.photoIds();
          return photos.keys().then(function (keys) {
            return Promise.all((keys || []).filter(function (k) { return !mine[k]; }).map(function (k) { return photos.del(k); }));
          }).catch(function () {});
        },
        lastBackupText: function () { this.rev; return this.ago(S.state && S.state.meta ? S.state.meta.lastBackup : null); },
        storageKb: function () { this.rev; var raw = lsGet(KEY); return raw ? Math.max(1, Math.round(raw.length * 2 / 1024)) : 0; },
        usageText: function () { return this.usage == null || this.usage < 512000 ? "" : this.t("data.usage", { mb: (Math.round(this.usage / 104857.6) / 10).toLocaleString(this.L === "es" ? "es-US" : "en-US") }); },

        /* ================= import: CSV or a full backup → preview → merge or replace ================= */
        impReset: function () { S.impRows = null; S.impPlan = null; S.impBackup = null; this.imp = { step: "pick", err: "", name: "" }; this.dragOver = false; },
        impDrop: function (ev) {
          this.dragOver = false;
          var file = ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files[0];
          if (file) this.impFile(file);
        },
        impPick: function (ev) { var file = ev.target.files && ev.target.files[0]; ev.target.value = ""; if (file) this.impFile(file); },
        // A CSV may weigh up to 10 MB; a full backup (every receipt photo inside) much more — its limit
        // is the core's (GVX.importKind / importLimit), checked once the file says what it is.
        impFile: function (file) {
          var self = this, X = S.X, most = X.importLimit("backup");
          this.impReset();
          this.imp.name = file.name;
          var tooBig = function (limit) { self.imp.err = self.t("imp.too_big", { mb: self.count(Math.round(limit / 1048576)) }); };
          if (file.size > most) { tooBig(most); return; }
          readText(file).then(function (text) {
            var t = String(text || "").replace(/^﻿/, ""), kind = X.importKind(file.name, t.slice(0, 64)), limit = X.importLimit(kind);
            if (file.size > limit) { tooBig(limit); return; }
            if (kind === "backup") self.impBackupText(t);
            else self.impCsvText(t);
          }, function () { self.imp.err = self.t("imp.unreadable"); });
        },
        impCsvText: function (text) {
          var X = S.X;
          if (!clean(text)) { this.imp.err = this.t("imp.empty"); return; }
          var rows = X.parseCSV(text);
          if (rows && rows.error) { this.imp.err = this.msgKey(rows.error); return; }
          S.impRows = rows;
          this.imp.kind = "csv";
          this.imp.opts = { dateOrder: this.L === "es" ? "dmy" : "mdy", decimal: "auto", includeDuplicates: false };
          this.imp.map = { date: "", description: "", amount: "", category: "", miles: "", notes: "" };
          this.imp.mapped = false;
          this.imp.forceMap = false;
          this.imp.mode = "merge";
          this.impPlan();
        },
        // "Map the columns myself": a file that looked like the tracker's own goes through the mapping step
        impMapMyself: function () { this.imp.forceMap = true; this.imp.mapped = false; this.impPlan(); },
        impPlan: function () {
          var X = S.X, im = this.imp, o = { dateOrder: im.opts.dateOrder, allowDuplicates: !!im.opts.includeDuplicates, lang: this.L, forceMapping: !!im.forceMap };
          if (im.opts.decimal !== "auto") o.decimal = im.opts.decimal;
          if (im.mapped) {
            var m = {};
            Object.keys(im.map).forEach(function (k) { if (im.map[k] !== "") m[k] = Number(im.map[k]); });
            o.mapping = m;
          }
          var plan;
          try { plan = X.planImport(S.impRows, S.state.entries, this.st(), o); } catch (e) { if (window.console) console.error("[expenses]", e); this.imp.err = this.t("imp.unreadable"); return; }
          if (!plan) { this.imp.err = this.t("imp.unreadable"); return; }
          var fatal = (plan.errors || []).filter(function (x) { return !x.row; })[0];
          if (fatal && !plan.needsMapping && !(plan.all || []).length) { this.imp.err = this.msgKey(fatal.message_key); return; }
          S.impPlan = plan;
          if (plan.needsMapping && !im.mapped) {
            this.imp.headers = (plan.headers || []).map(function (h, i) { return { i: i, name: clean(h) || ("#" + (i + 1)) }; });
            this.imp.sample = (plan.sample || []).slice(0, 5).map(function (r) { return (r || []).map(str); });
            this.impGuess();
            this.imp.step = "map";
            return;
          }
          this.impSummary(plan);
          this.imp.step = "preview";
        },
        // a first guess for the mapping: headers that look like date / description / amount …
        impGuess: function () {
          var im = this.imp, tests = {
            date: /date|fecha|day|d[ií]a/i, description: /desc|memo|detail|concept|what|item|payee|nota? de/i, amount: /amount|total|monto|importe|cost|price|precio|debit|\$/i,
            category: /categ/i, miles: /mile|milla|mi\b/i, notes: /note|nota|comment|coment/i,
          };
          Object.keys(tests).forEach(function (k) {
            if (im.map[k] !== "") return;
            var hit = im.headers.filter(function (h) { return tests[k].test(h.name); })[0];
            if (hit) im.map[k] = String(hit.i);
          });
        },
        // a date, and an amount or miles (a mileage log has no amount: the default rate gives it; the
        // description is optional — the core writes one for a trip)
        impMapReady: function () { var m = this.imp && this.imp.map; return !!m && m.date !== "" && (m.amount !== "" || m.miles !== ""); },
        impUseMap: function () { this.imp.mapped = true; this.impPlan(); },
        // a problem's field, as the visitor knows it: their own column's name (a mapped sheet), else the
        // field's name on this page
        impField: function (field) {
          var im = this.imp, m = im && im.map, i = m && im.mapped && m[field] !== undefined && m[field] !== "" ? Number(m[field]) : -1;
          var h = i >= 0 && im.headers ? im.headers.filter(function (x) { return x.i === i; })[0] : null;
          if (h) return h.name;
          var k = field === "amount_cents" ? "amount" : field;
          return k && S.ui["field." + k] ? this.t("field." + k) : (k || "—");
        },
        impSummary: function (plan) {
          var self = this, reasons = {};
          (plan.skip || []).forEach(function (s) { reasons[s.reason] = (reasons[s.reason] || 0) + 1; });
          this.imp.counts = { add: (plan.add || []).length, update: (plan.update || []).length, skip: (plan.skip || []).length, errors: (plan.errors || []).length,
                              dup: (reasons.duplicate || 0) + (reasons.duplicate_id || 0), older: reasons.older || 0, same: reasons.same || 0, all: (plan.all || []).length };
          this.imp.ours = plan.format === "ours";
          this.imp.newCats = (plan.newCategories || []).map(function (c) { return self.lbl(c.label || c.name || c); });
          this.imp.newFunders = (plan.newFunders || []).map(function (c) { return self.lbl(c.name || c.label || c); });
          this.imp.sampleRows = (plan.add || []).concat(plan.update || []).slice(0, 8).map(function (e, i) {
            return { i: i, date: self.day(e.date), desc: e.description || "", cat: self.lbl((plan.newCategories || []).filter(function (c) { return c.id === e.category; }).map(function (c) { return c.label; })[0]) || self.catLabel(e.category),
                     amount: e.type === "received" ? "+" + self.money(e.amount_cents) : e.type === "giveaway" || e.type === "stock" ? self.count(e.quantity || 0) : self.money(e.amount_cents) };
          });
          var probs = (plan.errors || []).concat(plan.warnings || []);
          this.imp.errorList = probs.slice(0, 20).map(function (x, i) {
            return { i: i, text: x.row ? self.t("imp.error_row", { row: x.row, field: self.impField(x.field), message: self.msgKey(x.message_key || x.key) }) : self.msgKey(x.message_key || x.key) };
          });
          this.imp.moreErrors = Math.max(0, probs.length - 20);
        },
        impBackupText: function (text) {
          var r;
          try { r = S.X.readBackup(text, S.cfg); } catch (e) { r = { ok: false, error: "expenses.err.backup_invalid" }; }
          if (!r || !r.ok) { this.imp.err = this.msgKey((r && r.error) || "expenses.err.backup_invalid"); return; }
          var st = r.state || {};
          S.impBackup = { entries: st.entries || [], settings: st.settings || null, receipts: r.receipts || st.receipts || [], meta: st.meta || null };
          this.imp.kind = "backup";
          this.imp.mode = "merge";
          this.imp.counts = { entries: S.impBackup.entries.length, photos: S.impBackup.receipts.length };
          this.imp.step = "backup";
        },
        impApply: function () {
          var self = this, im = this.imp, n = S.state.entries.length;
          var go = function () { if (im.kind === "backup") self.impApplyBackup(); else self.impApplyCsv(); };
          if (im.mode === "replace" && n) {
            this.confirm(this.t("ask.replace", { n: this.count(n) }), this.t("ask.replace_ok"), true).then(function (yes) { if (yes) go(); });
          } else go();
        },
        impApplyCsv: function () {
          var X = S.X, plan = S.impPlan, before = S.state.entries.length;
          var next = X.applyImport(S.state, plan, { mode: this.imp.mode });
          if (!next || !Array.isArray(next.entries)) { this.imp.err = this.t("imp.unreadable"); return; }
          next.settings = X.mergeDefaults(S.cfg, next.settings || S.state.settings);
          next.meta = next.meta || S.state.meta;
          S.state = next;
          this.save();
          if (this.imp.mode === "replace") this.cleanPhotos();   // the replaced entries' receipt photos go too
          var added = this.imp.mode === "replace" ? next.entries.length : Math.max(0, next.entries.length - before);
          this.imp = { step: "done", added: added, updated: (plan.update || []).length, err: "" };
          this.saySaved(this.t("toast.imported", { n: this.count(added) }));
          if (next.entries.length) this.askPersist();
        },
        // A full backup: replace, or merge by id (the newer copy of an entry wins; new list items are added).
        impApplyBackup: function () {
          var self = this, X = S.X, b = S.impBackup, mode = this.imp.mode, st = S.state, now = nowIso();
          var settings = mode === "replace" && b.settings ? X.mergeDefaults(S.cfg, b.settings) : st.settings;
          if (mode !== "replace" && b.settings) {
            ["categories", "funders", "methods", "rates", "budgets", "custom_fields"].forEach(function (k) {
              var have = {};
              (settings[k] || []).forEach(function (x) { have[x.id] = 1; });
              (b.settings[k] || []).forEach(function (x) { if (x && x.id && !have[x.id]) (settings[k] = settings[k] || []).push(x); });
            });
            settings.places = uniq((settings.places || []).concat(b.settings.places || []));
          }
          var entries, touched = {};
          if (mode === "replace") { entries = b.entries.slice(); entries.forEach(function (e) { touched[e.id] = 1; }); }
          else {
            var byId = {};
            st.entries.forEach(function (e) { byId[e.id] = e; });
            b.entries.forEach(function (e) {
              if (!e || !e.id) return;
              var old = byId[e.id];
              if (!old || String(e.updated || "") > String(old.updated || "")) { byId[e.id] = e; touched[e.id] = 1; }
            });
            entries = Object.keys(byId).map(function (k) { return byId[k]; });
          }
          entries = entries.map(function (e) { var r = X.normalizeEntry(e, settings); return r && r.entry ? r.entry : e; });
          var added = Object.keys(touched).length;
          var put = function () {
            return Promise.all((b.receipts || []).filter(function (r) { return r && touched[r.id]; }).map(function (r) {
              var blob = dataUrlToBlob(r.dataUrl);
              return blob ? photos.put({ id: r.id, type: blob.type || "image/jpeg", blob: blob, w: 0, h: 0, name: "", added: now }).catch(function () {}) : null;
            }));
          };
          (mode === "replace" ? photos.clear() : Promise.resolve()).then(put).then(function () {}, function () {});
          S.state = { v: st.v || 1, entries: entries, settings: settings, meta: Object.assign({}, st.meta || {}, { lastBackup: (b.meta && b.meta.lastBackup) || st.meta.lastBackup }) };
          this.save();
          this.imp = { step: "done", added: added, updated: 0, err: "" };
          this.saySaved(this.t("toast.imported", { n: this.count(added) }));
          if (entries.length) this.askPersist();
        },

        /* ================= examples, erase ================= */
        // once: with the examples already there (a second click) nothing is added twice
        addExamples: function () {
          if (this.hasExamples()) return;
          var ex = S.X.exampleEntries(today(), this.st(), this.L) || [];
          S.state.entries = S.state.entries.concat(ex);
          this.save();
          this.saySaved(this.t("toast.examples_added", { n: this.count(ex.length) }));
        },
        removeExamples: function () {
          var self = this, n = S.state.entries.filter(function (e) { return e.example; }).length;
          if (!n) return;
          this.confirm(this.t("ask.remove_examples", { n: this.count(n) }), this.t("ask.remove_ok"), true).then(function (yes) {
            if (!yes) return;
            var ids = [];
            S.state.entries = S.state.entries.filter(function (e) { if (e.example) { ids.push(e.id); return false; } return true; });
            ids.forEach(function (id) { delete self.sel[id]; photos.del(id); });
            self.save();
            self.saySaved(self.t("toast.examples_removed"));
          });
        },
        eraseReady: function () { return clean(this.eraseText).toUpperCase() === this.t("data.erase_word").toUpperCase(); },
        eraseAll: function () {
          var self = this;
          if (!this.eraseReady()) return;
          this.confirm(this.t("ask.erase"), this.t("ask.erase_ok"), true).then(function (yes) {
            if (!yes) return;
            lsDel(KEY);
            photos.clear();
            var st = S.X.emptyState(S.cfg);
            st.settings = S.X.mergeDefaults(S.cfg, st.settings || {});
            S.state = st;
            S.memo = {};
            self.sel = {};
            self.eraseText = "";
            self.rev++;
            self.say(self.t("toast.erased"));
          });
        },

        /* ================= Settings: every list is editable ================= */
        tones: function () { return (S.cfg && S.cfg.tones) || ["gv", "lv", "grape", "vine", "rose", "teal", "gold", "slate"]; },
        pickIcons: function () { return (S.cfg && S.cfg.icons) || []; },
        catTypes: function () { var self = this; return TYPES.map(function (id) { return { id: id, label: self.t("type_add." + id) }; }); },
        setGo: function (k) { if (SET_TABS.indexOf(k) !== -1) this.setTab = k; },
        toggleOpen: function (key) { this.open[key] = !this.open[key]; },
        // A settings list for the screen: fresh copies on every change. The settings live outside
        // Alpine's reactivity and are edited in place, so handing x-for the same objects again would
        // leave a renamed label, a new colour or icon, "hidden" … stale on screen until a reload.
        list: function (kind, type) {
          this.rev;
          var s = this.st(), l = (s[kind] || []).map(function (x) { return x && typeof x === "object" ? Object.assign({}, x) : x; });
          if (type) l = l.filter(function (x) { return x.type === type; });
          return kind === "categories" || kind === "funders" || kind === "methods" ? l.sort(this.byOrder) : l;
        },
        item: function (kind, id) { return (this.st()[kind] || []).filter(function (x) { return x.id === id; })[0] || null; },
        setField: function (kind, id, field, value) {
          var it = this.item(kind, id);
          if (!it) return;
          it[field] = value;
          this.save();
        },
        // a name the visitor typed is theirs: a plain string (mergeDefaults keeps it; a built-in {en, es}
        // pair follows the site's wording)
        setName: function (kind, id, field, value) {
          var it = this.item(kind, id), v = clean(value);
          if (!it || !v) { this.rev++; return; }
          it[field] = v;
          this.save();
        },
        nameOf: function (x, field) { return this.lbl(x[field || "label"]); },
        field: { categories: "category", funders: "funder", methods: "method" },
        move: function (kind, id, dir, type) {
          var l = this.list(kind, type), i = -1;
          l.forEach(function (x, k) { if (x.id === id) i = k; });
          var j = i + dir;
          if (i < 0 || j < 0 || j >= l.length) return;
          var a = l[i], real = {};
          l.splice(i, 1);
          l.splice(j, 0, a);
          // list() hands out copies: the new order goes on the stored items
          (this.st()[kind] || []).forEach(function (x) { real[x.id] = x; });
          l.forEach(function (x, k) { if (real[x.id]) real[x.id].order = k; });
          this.save();
          GV.announce && GV.announce(this.t("set.moved", { name: this.nameOf(a, kind === "categories" ? "label" : "name"), n: j + 1, total: l.length }));
          var self = this;
          this.$nextTick(function () {
            var want = dir < 0 ? "up" : "down", b = document.querySelector('[data-move="' + want + '"][data-id="' + id + '"]');
            if (!b || b.getAttribute("aria-disabled") === "true") b = document.querySelector('[data-move="' + (dir < 0 ? "down" : "up") + '"][data-id="' + id + '"]');
            if (b) b.focus();
          });
        },
        nextOrder: function (kind) { return (this.st()[kind] || []).reduce(function (m, x) { return Math.max(m, (x.order || 0) + 1); }, 0); },
        focusSoon: function (id) { this.$nextTick(function () { var el = document.getElementById(id); if (el) el.focus(); }); },
        addCategory: function () {
          var type = this.newCatType, id = S.X.newId();
          var tpl = type === "expense" ? "general" : type;
          this.st().categories.push({ id: id, type: type, template: tpl, icon: TYPE_ICON[type] || "shapes", color: "slate", label: this.t("set.new_category"), builtin: false, hidden: false, order: this.nextOrder("categories") });
          this.open["cat:" + id] = true;
          this.save();
          this.focusSoon("xp-s-cat-" + id);
        },
        addFunder: function (kind) {
          var id = S.X.newId();
          this.st().funders.push({ id: id, kind: kind || "other", name: this.t(kind === "person" ? "set.new_person" : "set.new_funder"), builtin: false, hidden: false, order: this.nextOrder("funders") });
          this.save();
          this.focusSoon("xp-s-fun-" + id);
        },
        addMethod: function () {
          var id = S.X.newId();
          this.st().methods.push({ id: id, name: this.t("set.new_method"), builtin: false, hidden: false, order: this.nextOrder("methods") });
          this.save();
          this.focusSoon("xp-s-met-" + id);
        },
        // delete a custom item nobody uses; a used one is merged into another first
        canDelete: function (kind, id) {
          var it = this.item(kind, id);
          if (!it || it.builtin || id === "me") return false;
          if (kind === "rates") return this.defaultRate().id !== id;
          return !this.field[kind] || !this.usedCount(this.field[kind], id);
        },
        del: function (kind, id) {
          var self = this, it = this.item(kind, id);
          if (!this.canDelete(kind, id)) return;
          this.confirm(this.t("ask.delete_item", { name: this.lbl(it.label || it.name) }), this.t("ask.delete_ok"), true).then(function (yes) {
            if (!yes) return;
            self.st()[kind] = self.st()[kind].filter(function (x) { return x.id !== id; });
            self.save();
            self.saySaved(self.t("toast.item_deleted"));
          });
        },
        mergeTargets: function (kind, id) {
          var it = this.item(kind, id);
          return this.list(kind).filter(function (x) { return x.id !== id && !x.hidden && (kind !== "categories" || x.type === it.type); });
        },
        merge: function (kind, id, into) {
          var self = this, f = this.field[kind], it = this.item(kind, id), to = this.item(kind, into);
          if (!f || !it || !to) return;
          var n = this.usedCount(f, id);
          this.confirm(this.t("ask.merge", { n: this.count(n), from: this.lbl(it.label || it.name), to: this.lbl(to.label || to.name) }), this.t("ask.merge_ok")).then(function (yes) {
            if (!yes) return;
            var ids = S.state.entries.filter(function (e) { return e[f] === id; }).map(function (e) { return e.id; });
            self.patch(ids, function (e) { e[f] = into; });
            if (it.builtin) it.hidden = true;
            else self.st()[kind] = self.st()[kind].filter(function (x) { return x.id !== id; });
            self.save();
            self.saySaved(self.t("toast.merged", { n: self.count(ids.length) }));
          });
        },
        /* ---- rates and places ---- */
        addRate: function () {
          var id = S.X.newId();
          this.st().rates.push({ id: id, name: this.t("set.new_rate"), rate: "", builtin: false });
          this.save();
          this.focusSoon("xp-s-rate-" + id);
        },
        setRate: function (id, v) {
          var s = clean(v).replace(",", ".").replace(/^\$/, "");
          if (s !== "" && !/^\d{0,2}(\.\d{1,3})?$/.test(s)) { this.say(this.t("set.rate_invalid")); this.rev++; return; }
          this.setField("rates", id, "rate", s);
        },
        setDefaultRate: function (id) { this.st().default_rate = id; if (this.st().defaults) this.st().defaults.rate = id; this.save(); },
        addPlace: function () {
          var v = clean(this.newPlace), s = this.st();
          if (!v) return;
          s.places = uniq((s.places || []).concat([v]));
          this.newPlace = "";
          this.save();
        },
        setPlace: function (i, v) { var s = this.st(); v = clean(v); if (v) s.places[i] = v; else s.places.splice(i, 1); this.save(); },
        delPlace: function (i) { this.st().places.splice(i, 1); this.save(); },
        movePlace: function (i, dir) {
          var p = this.st().places, j = i + dir;
          if (j < 0 || j >= p.length) return;
          var a = p.splice(i, 1)[0];
          p.splice(j, 0, a);
          this.save();
        },
        /* ---- budgets ---- */
        addBudget: function () {
          var s = this.st(), f = this.funders().filter(function (x) { return x.kind !== "self"; })[0];
          s.budgets = s.budgets || [];
          var id = S.X.newId();
          s.budgets.push({ id: id, funder: f ? f.id : "me", year: new Date().getFullYear(), amount_cents: 0, label: "" });
          this.save();
          this.focusSoon("xp-s-bud-" + id);
        },
        setBudgetAmount: function (id, v) {
          var c = this.moneyOf(v);
          if (c === null) { this.say(this.t("form.err_money")); this.rev++; return; }
          this.setField("budgets", id, "amount_cents", c === "" ? 0 : c);
        },
        delBudget: function (id) { var s = this.st(); s.budgets = (s.budgets || []).filter(function (b) { return b.id !== id; }); this.save(); },
        /* ---- custom fields ---- */
        addCustom: function () {
          var s = this.st(), id = S.X.newId();
          s.custom_fields = s.custom_fields || [];
          s.custom_fields.push({ id: id, label: this.t("set.new_field"), type: "text", options: [], types: ["expense"] });
          this.save();
          this.focusSoon("xp-s-cf-" + id);
        },
        setOptions: function (id, v) { this.setField("custom_fields", id, "options", uniq(String(v || "").split(/[,;]/))); },
        toggleCfType: function (id, type) {
          var it = this.item("custom_fields", id);
          if (!it) return;
          var l = (it.types || []).slice(), i = l.indexOf(type);
          if (i === -1) l.push(type); else l.splice(i, 1);
          it.types = l;
          this.save();
        },
        delCustom: function (id) {
          var self = this, it = this.item("custom_fields", id);
          this.confirm(this.t("ask.delete_item", { name: it ? it.label : "" }), this.t("ask.delete_ok"), true).then(function (yes) {
            if (!yes) return;
            var s = self.st();
            s.custom_fields = s.custom_fields.filter(function (c) { return c.id !== id; });
            self.save();
          });
        },
        /* ---- your details, reminders ---- */
        prof: function (k) { this.rev; return (this.st().profile || {})[k] || ""; },
        setProf: function (k, v) { var s = this.st(); s.profile = s.profile || {}; s.profile[k] = clean(v).slice(0, 80); this.save(); },
        setDays: function (k, v) {
          var n = Math.round(Number(v));
          if (!isFinite(n) || n < 1 || n > 365) { this.say(this.t("set.days_invalid")); this.rev++; return; }
          this.st()[k] = n;
          this.save();
        },
      };
    });
  });
})();
