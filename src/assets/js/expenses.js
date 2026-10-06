/* The service expense tracker on /tracker/ (src/pages/tracker.njk): the page's Alpine app, "xpApp".
   The data model, the money math, the summaries, CSV and backups live in expenses-core.js (window.GVX,
   loaded just before this file; tests/test_expenses_core.py). This file is the screen:
     · five views in a tab bar — Entries · Summary · Giveaways · Requests · Settings — remembered in the
       settings (ui.view) and in the address (#entries …), so links and the back button work;
     · the add / edit dialog (a native <dialog>), bulk changes with a 10-second undo;
     · Giveaways: the literature of a period (on hand at its start and end) and, below it, every
       subscription with where it stands (ending soon, ended, renewed …) and its calendar file (.ics);
     · the reimbursement request (print / copy / share / CSV / "mark as submitted") and the service
       report (what the service cost: money by category, miles by service activity; print / CSV);
     · import (a CSV, an Excel workbook or a backup: preview first, then merge or replace) and export
       (CSV; the full backup, a .zip with each receipt photo as a file — expenses-files.js; or the ledger
       alone, a .json "without photos"), with the backup's size worked out first;
     · receipt photos.
   Storage — only in this browser, as the page promises:
     localStorage "gv-expenses:v1"         {v, entries, settings, meta} (GVX owns the shape; migrate on load)
     localStorage "gv-expenses:v1:ui"      {view, period, sort, from, to}: the screen's own conveniences,
                                           apart, so a tab click never looks like new data to another tab
     localStorage "gv-expenses:v1:undo"    {photo id: until (ms)}: the receipt photos of deletes that can still
                                           be undone, in this tab or another — never deleted meanwhile
     localStorage "gv-expenses:v1:unreadable-YYYY-MM-DD"  a stored ledger that could not be read, kept aside
                                           as it was (never overwritten); the notice over the app offers it as a file
     IndexedDB "gv-expenses" / "receipts"  one photo per entry (key = the entry id), a downscaled JPEG;
                                           a photo no entry points to any more is deleted on load
   Every storage call is wrapped: in a private window (or with storage blocked, or full) the app still
   works in memory, warns to export before closing, and never says "Saved" for something it could not
   keep. A change made in another tab reloads the data here. A photo is deleted only once nothing points to
   it: not the ledger as stored now (another tab may have brought its entry back), not a pending undo.
   Closing the tab with the add / edit form changed (or photos still being restored) asks first.
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
  var UNDO_KEY = KEY + ":undo";
  var ASIDE = KEY + ":unreadable-";
  var DB_NAME = "gv-expenses";
  var DB_STORE = "receipts";
  var PAGE = 100;              // rows per "Show more"
  var UNDO_MS = 10000;         // how long "Undo" stays after a delete (paused while the toast has the focus or the mouse)
  var UNDO_KEEP = 30 * 60000;  // …and how long its photos stay safe from another tab's clean-up (the toast can be held)
  var MAX_PHOTO = 1600;        // longest side of a stored receipt photo (px)
  var BIG_BACKUP = 18 * 1048576;  // a full backup this big is too big for most e-mail (25 MB, encoded): the page says so
  var VIEWS = ["entries", "summary", "giveaways", "requests", "settings"];
  var TYPES = ["expense", "mileage", "received", "giveaway", "stock"];
  var CLAIMS = ["to_request", "submitted", "paid", "denied"];
  var SET_TABS = ["data", "profile", "categories", "funders", "methods", "activities", "mileage", "budgets", "fields", "reminders"];
  // the roles the form suggests for a trip (role.<id> in the page's words; the visitor types any other)
  var ROLES = ["attended", "table", "tech", "zoom", "projector", "presented", "chaired", "report"];
  // a subscription's status (GVX.subscriptions) → its icon in the list
  var SUB_ICON = { ending: "clock", ended: "circle-x", active: "circle-check", renewed: "repeat", no_end: "calendar-x" };
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
  // calendar days from then to today, on this device's calendar: a backup made at 11 PM last night was
  // "yesterday", not "today" (local midnights, rounded: a day with a clock change still counts one)
  function daysSince(iso) {
    if (!iso) return null;
    var t = new Date(iso.length === 10 ? iso + "T12:00:00" : iso), n = new Date();
    if (isNaN(t)) return null;
    return Math.round((new Date(n.getFullYear(), n.getMonth(), n.getDate()) - new Date(t.getFullYear(), t.getMonth(), t.getDate())) / 864e5);
  }
  function clone(o) { return o == null ? o : JSON.parse(JSON.stringify(o)); }
  function str(v) { return v == null ? "" : String(v); }
  function clean(s) { return str(s).replace(/\s+/g, " ").trim(); }
  // case-, accent- and space-insensitive (matching names typed on different devices)
  function norm(s) { return clean(s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, ""); }
  // a number typed in the form (miles, an odometer, a quantity), read as the money field reads money
  // (GVX): "42,150" is 42150 — a thousands separator, not a decimal comma — and "12,5" is still 12.5
  function num(v) {
    if (v === "" || v == null) return "";
    var X = window.GVX, n = X && X.parseNumber ? X.parseNumber(String(v), { decimal: "." }) : Number(String(v).replace(",", "."));
    return n !== null && isFinite(n) ? n : "";
  }
  function cents2str(c) { return c === "" || c == null || isNaN(c) ? "" : (Number(c) / 100).toFixed(2); }
  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } }
  function lsDel(k) { try { localStorage.removeItem(k); return true; } catch (e) { return false; } }
  // the stored keys that start with `prefix`
  function lsKeys(prefix) {
    var out = [];
    try { for (var i = 0; i < localStorage.length; i++) { var k = localStorage.key(i); if (k && k.indexOf(prefix) === 0) out.push(k); } } catch (e) { /* blocked */ }
    return out.sort();
  }
  // The receipt photos of deletes that can still be undone — here or in another tab ({id: until}).
  function undoPending() {
    var o = null, now = Date.now(), out = {};
    try { o = JSON.parse(lsGet(UNDO_KEY) || "null"); } catch (e) { o = null; }
    if (o && typeof o === "object") Object.keys(o).forEach(function (id) { if (Number(o[id]) > now) out[id] = Number(o[id]); });
    return out;
  }
  function undoMark(ids, on) {
    if (!ids.length) return;
    var o = undoPending();
    ids.forEach(function (id) { if (on) o[id] = Date.now() + UNDO_KEEP; else delete o[id]; });
    if (Object.keys(o).length) lsSet(UNDO_KEY, JSON.stringify(o)); else lsDel(UNDO_KEY);
  }
  // the photos the ledger AS STORED points to ({id: 1}) — {} when nothing is stored; null when it can't
  // be read (then no photo is deleted)
  function storedPhotoIds() {
    var raw = lsGet(KEY), out = {}, o;
    if (!raw) return out;
    try { o = JSON.parse(raw); } catch (e) { return null; }
    var list = Array.isArray(o) ? o : o && Array.isArray(o.entries) ? o.entries : null;
    if (!list) return null;
    list.forEach(function (e) { if (e && e.receipt === "photo" && e.id) out[e.id] = 1; });
    return out;
  }
  function breathe() { return new Promise(function (res) { setTimeout(res, 0); }); }
  // 1536 KB → "1.5 MB"; 900 KB → "900 KB" (the words: data.kb / data.mb)
  function sizeParts(bytes) {
    var mb = bytes / 1048576;
    return mb >= 1 ? { key: "data.mb", n: mb >= 10 ? Math.round(mb) : Math.round(mb * 10) / 10 } : { key: "data.kb", n: Math.max(1, Math.round(bytes / 1024)) };
  }

  /* Numbers and dates on screen: one Intl formatter per language and kind, made once for the page. The
     Requests view and the service report show hundreds of them per change, and a new formatter for each
     (GV.fmtDate makes one per call) took seconds on a slow phone. Dates are calendar days, formatted at
     noon UTC: the same day everywhere, as GV.fmtDate shows them. */
  var NUM_OPTS = { count: { maximumFractionDigits: 1 }, exact: { maximumFractionDigits: 6 } };
  var DAY_OPTS = { short: { month: "short", day: "numeric" }, mid: { month: "short", day: "numeric", year: "numeric" },
                   long: { month: "long", day: "numeric", year: "numeric" }, month: { month: "short", year: "numeric" } };
  var FMT = {};
  function fmtOf(kind, lang) {
    var k = kind + "|" + lang;
    if (!Object.prototype.hasOwnProperty.call(FMT, k)) {
      var loc = lang === "es" ? "es-US" : "en-US";
      try { FMT[k] = NUM_OPTS[kind] ? new Intl.NumberFormat(loc, NUM_OPTS[kind]) : new Intl.DateTimeFormat(loc, Object.assign({ timeZone: "UTC" }, DAY_OPTS[kind])); }
      catch (e) { FMT[k] = null; }
    }
    return FMT[k];
  }
  // "YYYY-MM-DD" (or "YYYY-MM": the 15th) in one of DAY_OPTS' kinds; GV.fmtDate, then the ISO day, where Intl fails
  function fmtDay(iso, kind, lang) {
    var noon = (iso.length === 7 ? iso + "-15" : iso.slice(0, 10)) + "T12:00:00Z", f = fmtOf(kind, lang), s = "";
    try { s = f ? f.format(new Date(noon)) : ""; } catch (e) { s = ""; }
    if (!s && GV.fmtDate) s = GV.fmtDate(noon, DAY_OPTS[kind]);
    return s || iso;
  }
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

  /* The date range of a period: this / last month, this / last year, a service panel ("panel:77": the
     panels offered, else Area 65's rule — GVX.panelById), everything (""), or the visitor's own dates.
     Inclusive ISO days. */
  function periodRange(p, panels, from, to) {
    var d = new Date(), y = d.getFullYear(), m = d.getMonth();
    if (p === "this_month") return { from: isoOf(new Date(y, m, 1)), to: isoOf(new Date(y, m + 1, 0)) };
    if (p === "last_month") return { from: isoOf(new Date(y, m - 1, 1)), to: isoOf(new Date(y, m, 0)) };
    if (p === "this_year") return { from: y + "-01-01", to: y + "-12-31" };
    if (p === "last_year") return { from: (y - 1) + "-01-01", to: (y - 1) + "-12-31" };
    if (p && p.indexOf("panel:") === 0) {
      var id = p.slice(6), hit = (panels || []).filter(function (x) { return x.id === id; })[0];
      if (!hit && window.GVX && window.GVX.panelById) hit = window.GVX.panelById(id);
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
  // A file's text. Read as bytes and decoded by GVX.decodeText: UTF-16 (Excel's "Unicode text"), UTF-8,
  // or Windows-1252 when the file is neither (Excel's "CSV" on Windows), so accented names never turn into "�".
  function bufferOf(blob) {
    return blob.arrayBuffer ? blob.arrayBuffer() : new Promise(function (res, rej) {
      var r = new FileReader(); r.onload = function () { res(r.result); }; r.onerror = function () { rej(r.error); }; r.readAsArrayBuffer(blob);
    });
  }
  function decode(buf) {
    var X = window.GVX;
    return X && X.decodeText ? X.decodeText(new Uint8Array(buf)) : new TextDecoder("utf-8").decode(buf);
  }
  function readText(file) { return bufferOf(file).then(decode); }
  // A file's first bytes, and as text: enough to tell a .zip, an old Excel file, a backup and a CSV apart.
  function sniff(file) {
    return bufferOf(file.slice ? file.slice(0, 64) : file).then(function (buf) { return { bytes: new Uint8Array(buf), text: decode(buf) }; });
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
    // x-xp-scroll on a table's box (role=region): a stop for the keyboard (tabindex 0, so a sideways scroll
    // can be reached without a mouse) only while its table is wider than the box — the service report's
    // fourteen tables, all in sight, are not fourteen Tab stops. Checked again whenever the box or its
    // table changes size (the window, the text size, the rows).
    Alpine.directive("xp-scroll", function (el, d, u) {
      var check = function () {
        if (el.scrollWidth > el.clientWidth + 1) el.setAttribute("tabindex", "0");
        else el.removeAttribute("tabindex");
      };
      check();
      if (!window.ResizeObserver) { el.setAttribute("tabindex", "0"); return; }   // (can't tell: reachable, as before)
      var ro = new ResizeObserver(check);
      ro.observe(el);
      if (el.firstElementChild) ro.observe(el.firstElementChild);
      u.cleanup(function () { ro.disconnect(); });
    });

    Alpine.data("xpApp", function (pageLang) {
      // Outside Alpine's reactivity (see the header): the data, the memo cache, timers, the pending photo.
      var S = { X: null, cfg: null, ui: {}, state: null, memo: {}, undo: null, undoT: 0, toastT: 0, flashT: 0,
                askResolve: null, opener: null, formSnap: "", formPerson: "", photo: null, photoUrl: "", rqUrls: [], persistTried: false,
                siteEvents: [] };

      return {
        L: pageLang === "es" ? "es" : "en",
        ready: false,
        broken: false,
        rev: 0,
        view: "entries",
        storageOk: true,
        // a stored ledger that could not be read is kept aside (damaged: how many copies; the notice offers
        // them); lock: why nothing is saved — "unreadable" (no room to keep it aside: it stays where it is)
        // or "newer" (a newer page saved it); "" = saving works
        damaged: 0,
        lock: "",
        persisted: null,
        usage: null,
        // the full backup's size, worked out before it is made (measureBackup): photos, bytes (the .zip),
        // plain (the .json without photos)
        bk: { ready: false, photos: 0, bytes: 0, plain: 0 },
        wide: true,               // the lists as tables (else cards): from 768px, below 130 % text
        subsWide: true,           // …the subscriptions' table: from 1024px, more with larger text (fitList)
        // Entries: filters (the period is shared with Summary and Giveaways), sort, paging, selection
        f: { q: "", period: "this_year", from: "", to: "", types: [], category: "", funder: "", status: "", activity: "", event: "", tag: "", receipt: "" },
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
        // Giveaways → Subscriptions: which ones the list shows ("" = all)
        subF: { status: "", kind: "" },
        // Requests
        rq: { funder: "", period: "this_year", from: "", to: "", st: { to_request: true, submitted: false, paid: false, denied: false }, names: false, photos: false, ref: "" },
        rqPhotos: [],
        // the service report: a year ("y:2026"), a panel, all dates or the visitor's own; every entry
        // listed or the totals only; names and notes left out unless asked (as on a request)
        rp: { period: "y:" + new Date().getFullYear(), from: "", to: "", detail: true, names: false, notes: false },
        // Settings
        setTab: "data",
        open: {},
        newCatType: "expense",
        newPlace: "",
        imp: null,
        dragOver: false,
        eraseText: "",
        ask: { msg: "", ok: "", danger: false, alt: "" },

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
          this.revealTab();     // the view reopened from the last visit, or asked for by the address
          // the address and the back button
          var onHash = function () { var v = self.hashView(); if (v && v !== self.view) self.go(v, false); };
          window.addEventListener("hashchange", onHash);
          window.addEventListener("popstate", onHash);
          // table ↔ cards: the width and the text size (the "Aa" panel); the subscriptions' table has a width of
          // its own that follows the text size, so any resize is checked (once a frame)
          if (window.matchMedia) {
            var mq = window.matchMedia("(min-width: 48rem)");
            if (mq.addEventListener) mq.addEventListener("change", function () { self.fitList(); self.revealTab(); });
          }
          var fitT = 0;
          window.addEventListener("resize", function () { if (!fitT) fitT = requestAnimationFrame(function () { fitT = 0; self.fitList(); }); });
          window.addEventListener("gvlv:prefs", function () { self.fitList(); self.revealTab(); });
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
          var root = document.documentElement, text = root.getAttribute("data-text") || "";
          var big = /^(130|150)$/.test(text);
          var mm = function (q) { return window.matchMedia ? window.matchMedia(q).matches : true; };
          this.wide = mm("(min-width: 48rem)") && !big;
          // The subscriptions' table (six columns and "Record the renewal") needs a laptop's width, and more at
          // 115 % text or with relaxed spacing (a media query's rem does not grow with the text, so the width
          // grows here); below that, the cards.
          var k = (text === "115" ? 1.15 : 1) * (root.getAttribute("data-spacing") === "relaxed" ? 1.1 : 1);
          this.subsWide = !big && mm("(min-width: " + Math.round(64 * k * 100) / 100 + "rem)");
        },

        /* ================= storage ================= */
        /* The stored ledger → S.state. One that can't be read (not JSON, not a ledger, or migrate fails) is
           never overwritten: a copy is kept beside it (ASIDE + the day; the notice over the app offers it as
           a file, and removes it) and the tracker starts empty — or, when the browser has no room for that copy, it is
           left where it is and nothing is saved over it (lock "unreadable") until the visitor has taken it.
           One saved by a newer version of the page (v above GVX.SCHEMA) is left as it is too: this page
           shows it but saves nothing (lock "newer") — normalizing it here would drop what it doesn't know. */
        loadState: function () {
          var X = S.X, raw = lsGet(KEY), st = null, bad = "", o = null;
          if (raw) {
            try { o = JSON.parse(raw); } catch (e) { bad = "unreadable"; }
            if (!bad && !(Array.isArray(o) || (o && typeof o === "object" && Array.isArray(o.entries)))) bad = "unreadable";
            if (!bad && !Array.isArray(o) && Number(o.v) > X.SCHEMA) bad = "newer";
            if (!bad || bad === "newer") { try { st = X.migrate(o, S.cfg); } catch (e) { st = null; bad = "unreadable"; } }
          }
          this.lock = "";
          if (bad === "unreadable" && !this.keepAside(raw)) this.lock = "unreadable";
          else if (bad === "newer") this.lock = "newer";
          this.damaged = lsKeys(ASIDE).length + (this.lock === "unreadable" ? 1 : 0);
          S.readOk = !!(raw && st && !bad);    // the ledger really came from this browser (cleanPhotos trusts only that)
          if (!st || typeof st !== "object") st = X.emptyState(S.cfg);
          st.entries = Array.isArray(st.entries) ? st.entries : [];
          st.settings = X.mergeDefaults(S.cfg, st.settings || {});
          st.meta = st.meta || { lastBackup: null, lastExport: null, created: nowIso() };
          S.state = st;
          S.memo = {};
          this.rev++;
        },
        // A copy of an unreadable ledger beside it (once: the same text already kept is not kept twice).
        // false: the browser had no room for it.
        keepAside: function (raw) {
          var have = lsKeys(ASIDE);
          for (var i = 0; i < have.length; i++) if (lsGet(have[i]) === raw) return true;
          var k = ASIDE + today(), n = 2;
          while (lsGet(k) !== null) k = ASIDE + today() + "-" + n++;
          return lsSet(k, raw);
        },
        // Writes the data; false when the browser would not keep it (the warning shows, and stays until
        // a save works again — space freed, for one), or when a ledger this page can't read is in the way
        // (lock: nothing is written over it).
        save: function () {
          var ok = !this.lock && lsSet(KEY, JSON.stringify(S.state));
          if (!this.lock) this.storageOk = ok;
          S.saveOk = ok;
          S.memo = {};
          this.rev++;
          return ok;
        },
        // the message after a change: never "Saved" (or "Deleted" …) when the last save failed
        saySaved: function (msg, withUndo) { this.say(S.saveOk === false ? this.t(this.lock ? "toast.not_saved" : "storage_off") : msg, withUndo); },
        // The unreadable ledger, as a file (each copy kept aside, or the one that is still where it was).
        damagedDownload: function () {
          var self = this, list = lsKeys(ASIDE).map(function (k) { return lsGet(k); });
          if (this.lock === "unreadable") list.push(lsGet(KEY));
          list.filter(Boolean).forEach(function (raw, i) {
            var name = self.t("data.file_base") + "-" + safeName(self.t("data.damaged_word")) + "-" + today() + (i ? "-" + (i + 1) : "") + ".json";
            saveBlob(new Blob([raw], { type: "application/json" }), name);
            self.say(self.t("toast.downloaded", { file: name }));
          });
        },
        // …and gone from this device, once the visitor says so (the tracker then saves again)
        damagedRemove: function () {
          var self = this;
          this.confirm(this.t("ask.damaged_remove"), this.t("ask.damaged_remove_ok"), true).then(function (yes) {
            if (!yes) return;
            lsKeys(ASIDE).forEach(lsDel);
            if (self.lock === "unreadable") { self.lock = ""; lsDel(KEY); if (S.state.entries.length) self.save(); }
            self.damaged = 0;
            self.say(self.t("toast.item_deleted"));
          });
        },
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
        // (GVX.fmtMoney keeps one currency formatter per language; count and day use the page's: fmtOf)
        money: function (c) {
          c = Number(c) || 0;
          try { if (S.X.fmtMoney) return S.X.fmtMoney(c, this.L); } catch (e) { /* fall through */ }
          return (c < 0 ? "-$" : "$") + (Math.abs(c) / 100).toFixed(2);
        },
        count: function (n) { var f = fmtOf("count", this.L); n = Number(n) || 0; return f ? f.format(n) : String(Math.round(n * 10) / 10); },
        // one-way miles as GVX.oneWayMiles works them out: every decimal they need to multiply back to the
        // total (12.65 for 25.3 mi there and back — count() would say 12.7, which doubles to 25.4), as the CSV has them
        oneWayText: function (n) { var f = fmtOf("exact", this.L); n = Number(n) || 0; return f ? f.format(n) : String(n); },
        plural: function (n, one, many) { return this.t(Number(n) === 1 ? one : many, { n: this.count(n) }); },
        day: function (iso, long) {
          if (!iso) return "";
          // long: "September 27, 2026" · "mid": "Sep 27, 2026" (the printed request) · else "Sep 27" (+ the year when not this year)
          var kind = long === true ? "long" : long === "mid" || iso.slice(0, 4) !== String(new Date().getFullYear()) ? "mid" : "short";
          return fmtDay(iso, kind, this.L);
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
            var s = this.st(), m = { cat: {}, fun: {}, met: {}, act: {} };
            (s.categories || []).forEach(function (c) { m.cat[c.id] = c; });
            (s.funders || []).forEach(function (f) { m.fun[f.id] = f; });
            (s.methods || []).forEach(function (x) { m.met[x.id] = x; });
            (s.activities || []).forEach(function (x) { m.act[x.id] = x; });
            return m;
          }) || { cat: {}, fun: {}, met: {}, act: {} };
        },
        cat: function (id) { return this.maps().cat[id] || null; },
        catLabel: function (id) { var c = this.cat(id); return c ? this.lbl(c.label) : (id || this.t("list.no_category")); },
        catIcon: function (id) { var c = this.cat(id); return c && c.icon ? c.icon : "shapes"; },
        catTone: function (id) { var c = this.cat(id); return "xp-tone-" + (c && c.color ? c.color : "slate"); },
        funder: function (id) { return this.maps().fun[id] || null; },
        funderName: function (id) { var f = this.funder(id); return f ? this.lbl(f.name) : (id || ""); },
        isSelf: function (id) { var f = this.funder(id); return !id || id === "me" || !!(f && f.kind === "self"); },
        methodName: function (id) { var m = this.maps().met[id]; return m ? this.lbl(m.name) : (id || ""); },
        // a service activity's name ("" for none: the caller says "no activity" in its own words)
        actName: function (id) { var a = this.maps().act[id]; return a ? this.lbl(a.name) : (id || ""); },
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
        activities: function (keep) { return (this.st().activities || []).filter(function (a) { return !a.hidden || a.id === keep; }).slice().sort(this.byOrder); },
        // the roles a trip's form suggests: the usual ones in the page's words, then the ones typed before
        roleSuggest: function () {
          var self = this;
          return uniq(ROLES.map(function (k) { return self.t("role." + k); }).concat(this.suggest("role")));
        },
        rates: function () { return this.st().rates || []; },
        defaultRate: function () {
          var s = this.st(), id = s.default_rate || (s.defaults && s.defaults.rate), list = this.rates();
          return list.filter(function (r) { return r.id === id; })[0] || list[0] || { id: "", rate: "" };
        },
        // the service panels the period filters offer (GVX.servicePanels): today's, each one with entries, and
        // the ones config/expenses.yml lists — newest first
        panels: function () {
          var day = today();
          return this.memo("panels", day, function () {
            var listed = this.st().panels || (S.cfg && S.cfg.panels) || [];
            return S.X.servicePanels ? S.X.servicePanels(listed, day, S.state.entries) : listed;
          }) || [];
        },
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
          this.revealTab();
        },
        /* On a phone the tab row scrolls sideways, and the open tab can sit off its edge: after "Build a
           request", a /tracker/#requests link, or the last view reopened on a new visit. A tab that is
           not wholly clear of the row's fades (its padding-right wide at the end, as wide at the start
           once scrolled — main.css chip-row-nowrap) goes to its own snap point: its start at the row's
           scroll-padding (expenses.css), so the row's snapping leaves it there. Only the row's own
           scrollLeft changes: scrollIntoView would also move the page. */
        revealTab: function () {
          var self = this;
          this.$nextTick(function () {
            var b = document.getElementById("xp-tab-" + self.view), row = b && b.parentElement;
            if (!row || row.scrollWidth <= row.clientWidth + 1) return;
            var cs = window.getComputedStyle ? window.getComputedStyle(row) : {};
            var fade = parseFloat(cs.paddingRight) || 0, lead = parseFloat(cs.scrollPaddingLeft) || 0;
            var r = b.getBoundingClientRect(), box = row.getBoundingClientRect();
            if (r.left >= box.left + (row.scrollLeft > 4 ? fade : 0) - 1 && r.right <= box.right - fade + 1) return;
            var x = row.scrollLeft + r.left - box.left - lead;
            row.scrollLeft = Math.max(0, Math.min(x, row.scrollWidth - row.clientWidth));
          });
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
          this.go(VIEWS[j]);     // (go brings the tab into view in the row)
          var b = document.getElementById("xp-tab-" + VIEWS[j]);
          if (b) b.focus();
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
        moreCount: function () { var f = this.f; return ["category", "funder", "status", "activity", "event", "tag", "receipt"].filter(function (k) { return f[k] !== ""; }).length; },
        anyFilter: function () { return !!(this.f.q || this.f.types.length || this.moreCount()); },
        clearFilters: function () {
          var f = this.f;
          f.q = ""; f.types = []; f.category = ""; f.funder = ""; f.status = ""; f.activity = ""; f.event = ""; f.tag = ""; f.receipt = "";
        },
        filtered: function () {
          var f = this.f, key = JSON.stringify(f) + "|" + this.sort;
          return this.memo("filtered", key, function () {
            var X = S.X, r = this.range();
            // the activity filter: one of the list, or "-" for the entries that have none
            var q = { q: clean(f.q), types: f.types.slice(), categories: f.category ? [f.category] : [], funders: f.funder ? [f.funder] : [],
                      statuses: f.status ? [f.status] : [], activities: f.activity ? [f.activity === "-" ? "" : f.activity] : [],
                      event: f.event, tag: f.tag, from: r.from, to: r.to };
            if (f.receipt !== "") q.hasReceipt = f.receipt === "yes";
            var list = X.filterEntries(S.state.entries, q, this.st()) || [];
            var s = SORTS[this.sort] || SORTS.date_desc;
            // (by the category names on screen: the page's language)
            return X.sortEntries(list, s[0], s[1], this.st(), this.L) || list;
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
          var rode = t === "mileage" && !!e.no_miles;
          if (t === "mileage" && (e.from || e.to)) add(clean(e.from) + " → " + clean(e.to));
          if (t === "mileage" && Number(e.trips) > 1) add(self.t(e.round_trip ? "list.trips_round" : "list.trips", { n: self.count(e.trips) }));
          if (e.item) add(e.item + (e.quantity !== "" && e.quantity != null && t !== "giveaway" && t !== "stock" ? " × " + self.count(e.quantity) : ""));
          else if (Number(e.quantity) > 1 && S.X.isSub(this.st(), e)) add(self.t("list.subs_qty", { n: self.count(e.quantity) }));
          // a trip with no miles: whom you rode with (or just that you did)
          if (rode) add(e.person ? self.t("list.rode_with", { name: clean(e.person) }) : self.t("list.rode"));
          else add(e.person);
          add(e.event);
          add(e.role);
          if (e.activity) add(self.actName(e.activity));
          if (!e.item) add(e.vendor);
          var amount, flow = "out";
          if (t === "received") { amount = "+" + self.money(e.amount_cents); flow = "in"; }
          else if (t === "giveaway") { amount = self.t("list.qty_given", { n: self.count(e.quantity || 0) }); flow = "items"; }
          else if (t === "stock") { amount = self.t("list.qty_in", { n: self.count(e.quantity || 0) }); flow = "items"; }
          else if (rode) { amount = self.t("list.no_miles"); flow = "items"; }
          else amount = self.money(e.amount_cents);
          var status = e.claim_status || "none";
          var showStatus = (t === "expense" || t === "mileage") && status !== "none";
          return {
            id: e.id, type: t, date: self.day(e.date), iso: e.date,
            desc: e.description || self.catLabel(e.category),
            sub: sub.join(" · "),
            miles: t === "mileage" && !rode ? self.t("list.miles", { n: self.count(e.miles || 0) }) : "",
            cat: self.catLabel(e.category), icon: self.catIcon(e.category), tone: self.catTone(e.category),
            funder: t === "giveaway" || rode ? "" : self.funderName(e.funder),
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
          this.downloadCsv(list, safeName(this.t("data.selected_word")));    // the file's name in the page's language
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
            // the photos stay until the undo time is over — marked for the other tabs too, so their clean-up
            // leaves them alone meanwhile
            S.undo = { entries: gone, photoIds: gone.filter(function (e) { return e.receipt === "photo"; }).map(function (e) { return e.id; }) };
            undoMark(S.undo.photoIds, true);
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
          var u = S.undo, have = {};
          if (!u) return;
          S.undo = null;
          undoMark(u.photoIds, false);
          // (an entry another tab brought back meanwhile is there once)
          S.state.entries.forEach(function (e) { have[e.id] = 1; });
          S.state.entries = S.state.entries.concat(u.entries.filter(function (e) { return !have[e.id]; }));
          this.save();
          this.saySaved(this.t("toast.restored"));
        },
        // the undo window is over (or a new delete starts one): the photos of deleted entries go — unless
        // something still points to them (dropPhotos)
        finishUndo: function () {
          var u = S.undo;
          S.undo = null;
          if (!u || !u.photoIds.length) return;
          undoMark(u.photoIds, false);
          this.dropPhotos(u.photoIds);
        },
        /* Deletes receipt photos — only the ones nothing points to: not an entry here, not one of the ledger
           as it is stored NOW (another tab may have brought its entry back: an undo, an import), not a delete
           that can still be undone here or in another tab. A stored ledger that can't be read keeps them all. */
        dropPhotos: function (ids) {
          var keep = this.photoIds(), stored = storedPhotoIds();
          if (stored === null || this.lock) return Promise.resolve(0);
          var gone = (ids || []).filter(function (id) { return !keep[id] && !stored[id]; });
          return Promise.all(gone.map(function (id) { return photos.del(id); })).then(function () { return gone.length; });
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
        // The page's own "Are you sure?" (a modal <dialog>): resolves true / false — or "alt" for a third
        // choice, when one is named (alt: its button's words)
        confirm: function (msg, ok, danger, alt) {
          var self = this;
          return new Promise(function (res) {
            if (S.askResolve) S.askResolve(false);
            S.askResolve = res;
            self.ask = { msg: msg, ok: ok || self.t("ask.ok"), danger: !!danger, alt: alt || "" };
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
          if (r) r(v === "alt" ? "alt" : !!v);
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
          // "More details" opens when it holds something (a hotel's name, city and confirmation are in the form itself)
          var lodging = this.tpl() === "lodging";
          this.formMore = !!(e.method && e.method !== (this.st().defaults || {}).method) || !!(e.notes || (e.tags && e.tags.length) || e.claim_ref || e.claim_date)
            || !!((e.vendor || e.place || e.ref) && !lodging);
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
          // the name the entry came with (buildEntry keeps it on a trip that was driven: no field shows it there)
          S.formPerson = this.form ? str(this.form.person) : "";
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
        /* Closing the tab (or leaving the page) while the form holds something unsaved — or while a backup's
           photos are still being restored — asks first. The listener is there only meanwhile: a page with
           nothing unsaved has none (the browser can keep it in its back-forward cache). The form calls this
           on every input and change. */
        armLeave: function () {
          var busy = (!!this.form && (this.dirty() || !!S.photo)) || !!S.restoring;
          if (busy && !S.onLeave) {
            S.onLeave = function (e) { e.preventDefault(); e.returnValue = ""; return ""; };
            window.addEventListener("beforeunload", S.onLeave);
          } else if (!busy && S.onLeave) {
            if (window.removeEventListener) window.removeEventListener("beforeunload", S.onLeave);
            S.onLeave = null;
          }
        },
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
          this.armLeave();
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
            vendor: "", event: "", activity: "", role: "", ref: "", place: "", person: "", person_name: "", item: "", format: "", quantity: "", unit_cost: "",
            giveaway: !!c.giveaway_default,
            miles: "", rate_id: r.id || "", rate: str(r.rate), from: "", to: "", round_trip: !!d.round_trip, trips: "", no_miles: false, odometer_start: "", odometer_end: "",
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
          // the miles as typed: one way when the round trip doubled them and the trips multiplied them (never
          // with the odometer) — GVX.oneWayMiles: the fewest decimals that multiply back to the same total,
          // so saving an edit never moves the miles (25.3 is 12.65 one way; 12.7 would save 25.4)
          var odo = e.odometer_start !== "" && e.odometer_start != null && e.odometer_end !== "" && e.odometer_end != null;
          if (e.type === "mileage" && (e.round_trip || Number(e.trips) > 1) && !odo && !e.no_miles && e.miles !== "" && e.miles != null) {
            f.miles = str(S.X.oneWayMiles(e.miles, e.round_trip, e.trips));
          }
          // the rate kept on the entry: its rate in the list, else "kept" (changing settings never changes old entries)
          var hit = this.rates().filter(function (r) { return String(r.rate) === String(e.rate); })[0];
          f.rate_id = hit ? hit.id : (e.type === "mileage" ? "kept" : f.rate_id);
          f.rate = e.type === "mileage" ? str(e.rate) : f.rate;
          // who pays it back: their funder's name — or, for a purchase made for someone and left on "me"
          // (an import, the example), the name on the entry (the form requires one to save)
          var fu = this.funder(e.funder);
          f.person_name = fu && fu.kind === "person" ? self.lbl(fu.name) : (e.sub_kind === "helped" ? str(e.person) : "");
          return f;
        },
        // the dialog's name (and the screen reader's): what is being recorded — a trip with "I didn't drive"
        // ticked is "A trip (no miles)", never "Miles driven" over a form with no miles in it
        formTitle: function () {
          var f = this.form;
          if (!f || this.formStep === 1) return this.t("form.title_what");
          return this.t((this.formMode === "edit" ? "form.title_edit_" : "form.title_add_") + (f.type === "mileage" && f.no_miles ? "ride" : f.type));
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
          // a trip with no miles ("I didn't drive") is a record of the event: no money, no request, no receipt
          var rode = t === "mileage" && !!f.no_miles;
          var T = {
            item: ["books", "printing", "giveaway", "stock"], format: ["books", "giveaway", "stock"],
            quantity: ["books", "printing", "giveaway", "stock", "subscription"],
            unit_cost: ["books"], giveaway: ["books"], subscription: ["subscription"], lodging: ["lodging"], attendees: ["meal"],
            mileage: ["mileage"], money: ["general", "books", "subscription", "lodging", "meal", "printing", "travel", "received"],
            // the last day of a stay or of a trip that spans days (an assembly, a convention); the role at an
            // event; an order / confirmation / check number (a hotel shows it with its name and city)
            end_date: ["lodging", "mileage"], role: ["mileage"], ref: ["general", "books", "subscription", "lodging", "meal", "printing", "travel"],
          };
          if (field === "funder") return f.type !== "giveaway" && !(t === "subscription" && f.sub_kind === "helped") && !rode;
          if (field === "status") return (f.type === "expense" || f.type === "mileage") && !this.isSelf(f.funder) && f.sub_kind !== "helped" && !rode;
          if (field === "method") return f.type === "expense" || (f.type === "mileage" && !rode) || f.type === "received";
          if (field === "receipt") return f.type !== "giveaway" && f.type !== "stock" && !rode;
          // the service activity: what you spend, drive and give at a service event
          if (field === "activity") return f.type === "expense" || f.type === "mileage" || f.type === "giveaway";
          if (field === "trips") return t === "mileage" && !rode && !this.odo();
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
        // the miles that count: none for "I didn't drive"; the odometer (the whole trip); else the miles × 2
        // for a round trip × the number of trips (GVX.tripMiles: three days at a convention, 58.7 mi one
        // way, there and back = 352.2)
        milesValue: function () {
          var f = this.form;
          if (!f || f.no_miles) return 0;
          if (this.odo()) return Math.max(0, Math.round((num(f.odometer_end) - num(f.odometer_start)) * 10) / 10);
          var m = num(f.miles);
          if (m === "") return 0;
          return S.X.tripMiles(m, !!f.round_trip, "", "", f.trips);
        },
        mileagePreview: function () {
          var f = this.form, m = this.milesValue();
          if (!f || !m || f.rate === "") return "";
          var c = 0, n = S.X.tripCount(f.trips);
          try { c = S.X.mileageCents(m, f.rate); } catch (e) { return ""; }
          // several trips: the sum says how the miles were worked out
          if (n > 1 && !this.odo()) {
            return this.t(f.round_trip ? "form.preview_round_trips" : "form.preview_trips", { n: this.count(n), each: this.count(S.X.tripMiles(num(f.miles), !!f.round_trip, "", "", 1)),
              miles: this.count(m), rate: f.rate, amount: this.money(c) });
          }
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
        /* The form → an entry. An edit starts from the entry as it is: a field its form does not show keeps
           what the entry has (an imported trip's quantity, a hotel's nights from a CSV, a purchase's
           attendees) — fixing a typo never erases them. A field the form shows is the form's. Only a new
           category (another form, other fields) leaves out what the new form has no place for, as a new
           entry does; and a trip ticked "I didn't drive" keeps no route, money or receipt. */
        buildEntry: function () {
          var f = this.form, t = f.type, tp = this.tpl(), errs = [], self = this;
          var cur = this.formMode === "edit" && f.id ? S.state.entries.filter(function (x) { return x.id === f.id; })[0] : null;
          var o = cur && cur.type === t && cur.category === f.category ? cur : null;
          var rode = tp === "mileage" && !!f.no_miles;
          // what a field the form doesn't show becomes: the entry's own value on an edit, else blank
          var kept = function (k, blank) { return o && o[k] !== undefined && o[k] !== null ? clone(o[k]) : blank === undefined ? "" : blank; };
          var shown = function (field, k, v) { return self.has(field) ? v : kept(k); };
          var e = {
            id: f.id, type: t, date: f.date, end_date: shown("end_date", "end_date", f.end_date), category: f.category,
            description: clean(f.description), funder: f.funder, claim_status: f.claim_status,
            claim_date: f.claim_date, claim_ref: clean(f.claim_ref), paid_date: f.paid_date,
            method: rode ? "" : shown("method", "method", f.method), ref: shown("ref", "ref", clean(f.ref)), vendor: clean(f.vendor), event: clean(f.event),
            activity: shown("activity", "activity", f.activity), role: shown("role", "role", clean(f.role)), place: clean(f.place),
            // a subscription's person: the field on screen first ("Who pays you back" for a purchase made
            // for someone, else "For whom"), then the other — the name the form filled in for a purchase
            // made for someone never overrides the one typed after it became a gift. A trip with no miles:
            // whom you rode with (the field it shows). A trip that was driven shows no such field: it keeps
            // the name it came with (an import's person column — an edit never drops it unseen), never one
            // typed for a ride and then unticked
            person: this.has("subscription") ? clean(f.sub_kind === "helped" ? f.person_name || f.person : f.person || f.person_name)
              : tp === "mileage" && !f.no_miles ? clean(S.formPerson) : clean(f.person),
            item: shown("item", "item", clean(f.item)),
            format: shown("format", "format", f.format), quantity: shown("quantity", "quantity", num(f.quantity)),
            unit_cost_cents: kept("unit_cost_cents"), giveaway: this.has("giveaway") ? !!f.giveaway : !!kept("giveaway", false),
            // a trip's numbers come from its form below; any other entry keeps the ones it has (an import's)
            miles: kept("miles"), rate: kept("rate"), from: kept("from"), to: kept("to"), round_trip: !!kept("round_trip", false), trips: kept("trips"),
            no_miles: false, odometer_start: kept("odometer_start"), odometer_end: kept("odometer_end"),
            // (a stay's nights follow its dates — GVX works them out when both are there)
            nights: kept("nights"), attendees: shown("attendees", "attendees", num(f.attendees)),
            sub_product: kept("sub_product"), sub_term: kept("sub_term"), sub_start: kept("sub_start"), sub_kind: kept("sub_kind"), repaid: kept("repaid"),
            receipt: rode ? "none" : this.has("receipt") ? f.receipt : kept("receipt", "none"), receipt_ref: clean(f.receipt_ref),
            tags: uniq(String(f.tags || "").split(/[,;]/)), notes: String(f.notes || "").trim(), custom: clone(f.custom || {}),
            example: !!f.example, created: f.created || "", amount_cents: 0,
          };
          if (this.has("money")) {
            var auto = this.booksAuto(), c = auto ? Math.round(num(f.quantity) * this.moneyOf(f.unit_cost)) : this.moneyOf(f.amount);
            // the amount is required: left empty it is an error (a typed 0 is fine); a minus sign is
            // not a way to record money coming in (that is "Money received"). A unit cost that isn't a
            // number has its own message below, and is why the amount could not be worked out: one
            // message, not two.
            var badUnit = this.has("unit_cost") && clean(f.unit_cost) !== "" && this.moneyOf(f.unit_cost) === null;
            if (!auto && clean(f.amount) === "") { if (!badUnit) errs.push({ field: "amount", text: this.t("form.err_amount_required") }); }
            else if (c === null) errs.push({ field: "amount", text: this.t("form.err_money") });
            else if (!auto && this.negative(f.amount)) errs.push({ field: "amount", text: this.t("form.err_amount_negative") });
            e.amount_cents = c === null || c === "" ? "" : c;
          }
          if (this.has("unit_cost")) {
            var u = this.moneyOf(f.unit_cost);
            if (u === null) errs.push({ field: "unit_cost", text: this.t("form.err_money") });
            e.unit_cost_cents = u === null ? "" : u;
          }
          if (tp === "mileage" && f.no_miles) {
            // "I didn't drive": the event, the role and whom you rode with — no route, miles or money
            // (GVX keeps it at $0, never asked for), so nobody pays for it either: "me"
            e.no_miles = true;
            e.funder = "me";
            e.from = ""; e.to = ""; e.miles = ""; e.rate = ""; e.round_trip = false; e.trips = ""; e.odometer_start = ""; e.odometer_end = "";
          } else if (tp === "mileage") {
            e.from = clean(f.from); e.to = clean(f.to); e.round_trip = !!f.round_trip && !this.odo();
            e.odometer_start = num(f.odometer_start); e.odometer_end = num(f.odometer_end);
            e.trips = this.odo() ? "" : num(f.trips);
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
            } else e.repaid = "";               // (a gift, your own, the group's: nobody pays it back)
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
          // is now kept some other way: a photo nothing points to never stays behind; once the entry
          // that no longer points to it is saved: dropPhotos checks the stored ledger)
          var drop = false;
          if (S.photo && S.photo !== "remove" && e.receipt === "photo") {
            var p = S.photo;
            photos.put({ id: e.id, type: "image/jpeg", blob: p.blob, w: p.w, h: p.h, name: p.name || "", added: now })
              .catch(function () { self.say(self.t("toast.photo_failed")); });
          } else if (S.photo === "remove" || (S.formOrig && S.formOrig.receipt === "photo" && e.receipt !== "photo")) drop = true;
          S.photo = null;
          // money a person paid back settles what was bought for them (oldest first)
          var settled = e.type === "received" ? this.settle(e.funder, e.date) : 0;
          var stored = this.save();
          if (stored) this.askPersist();
          if (stored && drop) this.dropPhotos([e.id]);
          this.flash(e.id);
          var msg = first ? this.t("toast.saved_first") : this.t("toast.saved");
          if (settled) msg += " · " + this.plural(settled, "toast.settled_one", "toast.settled");
          this.saySaved(msg);
          if (again) {
            var keep = this.form, nf = this.blankForm(keep.type, keep.category);
            // (the same event: its service activity and your role there come along too)
            ["date", "funder", "claim_status", "method", "event", "activity", "role", "place", "rate_id", "rate", "round_trip", "from", "sub_kind", "format"].forEach(function (k) { nf[k] = keep[k]; });
            this.form = nf;
            this.formMode = "add";
            this.clearPhoto();
            S.formSnap = JSON.stringify(nf);
            S.formPerson = "";
            this.armLeave();
            this.formErr = {}; this.formErrs = [];
            this.dlgMsg = "";
            this.$nextTick(function () { self.dlgMsg = self.t("form.saved_next"); });
            this.focusForm();
          } else {
            S.formSnap = JSON.stringify(this.form);    // (saved: nothing left to lose)
            this.armLeave();
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
            self.armLeave();
            GV.announce && GV.announce(self.t("form.photo_added"));
          }, function () { self.photoBusy = false; self.say(self.t("toast.photo_failed")); });
        },
        removePhoto: function () {
          if (S.photoUrl) URL.revokeObjectURL(S.photoUrl);
          S.photoUrl = ""; this.photoUrl = "";
          S.photo = "remove";
          this.form.receipt = "none";
          this.armLeave();
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
            var pct = Math.round(x.cents / total * 100), c = self.cat(x.id);
            // what was bought, as things: 30 items, 2 books — or, for subscriptions, "13 subscriptions" (the
            // word the Giveaways list and the report use for them); none for a hotel or miles
            var subs = !!c && c.template === "subscription";
            return { id: x.id, label: self.catLabel(x.id), icon: self.catIcon(x.id), tone: self.catTone(x.id), amount: self.money(x.cents), share: self.t("sum.share", { n: pct }),
                     items: !x.items ? "" : subs ? self.plural(x.items, "sum.items_subs_one", "sum.items_subs") : self.plural(x.items, "sum.items_one", "sum.items"),
                     w: Math.max(2, Math.round(x.cents / max * 100)), n: x.count };
          });
        },
        // By service activity: what each kind of service cost (its trips and its expenses), its miles and
        // trips, in the visitor's order of the activities; "" (none chosen) last
        actRows: function () {
          var self = this, list = (this.sum().by_activity || []).filter(function (a) { return a.cents || a.trips; });
          var max = list.reduce(function (m, a) { return Math.max(m, a.cents); }, 0) || 1;
          return list.map(function (a) {
            // "184.6 mi · 1 trip" — or only "1 trip" for a trip made riding with someone (no miles)
            var trips = a.trips ? self.plural(a.trips, "sum.trips_one", "sum.trips") : "";
            return { id: a.id || "-", label: a.id ? self.actName(a.id) : self.t("sum.no_activity"), amount: self.money(a.cents),
                     line: a.trips && a.miles ? self.t("sum.act_line", { miles: self.count(a.miles), trips: trips }) : trips,
                     w: a.cents ? Math.max(2, Math.round(a.cents / max * 100)) : 0 };
          });
        },
        // a part of another view (the Summary's "See every subscription" → Giveaways · Subscriptions): open
        // the view, then bring the part to the top and give it the focus (its heading has tabindex -1)
        jump: function (view, id) {
          if (view && view !== this.view) this.go(view);
          var tries = 0, run = function () {
            var el = document.getElementById(id);
            if (!el || !el.getClientRects().length) { if (tries++ < 10) requestAnimationFrame(run); return; }
            el.scrollIntoView({ block: "start" });
            el.focus({ preventScroll: true });
          };
          this.$nextTick(run);
        },
        monthName: function (ym) { return fmtDay(ym, "month", this.L); },
        byMonth: function () {
          var self = this, list = (this.sum().by_month || []).slice().sort(function (a, b) { return a.ym < b.ym ? -1 : 1; });
          var max = list.reduce(function (a, x) { return Math.max(a, x.spent || 0, x.received || 0); }, 0) || 1;
          return list.map(function (x) {
            return { ym: x.ym, label: self.monthName(x.ym), spent: self.money(x.spent), received: self.money(x.received),
                     ws: (x.spent ? Math.max(2, Math.round(x.spent / max * 100)) : 0), wr: (x.received ? Math.max(2, Math.round(x.received / max * 100)) : 0) };
          });
        },
        /* "Who owes you": each one's balance as it stands at the period's END — everything up to its last day
           counts, so a hotel claimed in December and paid back in January is even in January's view (the
           period alone would say "you hold $300 of theirs"). Listed: whoever still owes or is owed then, or
           had something in the period. */
        balances: function () {
          var self = this, r = this.range();
          return this.memo("bal", r.from + "|" + r.to, function () {
            var X = S.X, st = this.st(), upTo = { to: r.to }, active = {};
            (X.funderBalances(S.state.entries, st, { from: r.from, to: r.to }) || []).forEach(function (b) { if (b.claimed_cents || b.received_cents) active[b.funder] = 1; });
            return (X.funderBalances(S.state.entries, st, upTo) || []).filter(function (b) {
              return !self.isSelf(b.funder) && (b.balance_cents || b.to_request_cents || b.submitted_cents || active[b.funder]);
            }).map(function (b) {
              return { id: b.funder, name: self.funderName(b.funder), person: (self.funder(b.funder) || {}).kind === "person",
                       claimed: self.money(b.claimed_cents), toRequest: self.money(b.to_request_cents), submitted: self.money(b.submitted_cents),
                       paid: self.money(b.paid_cents), received: self.money(b.received_cents), balance: b.balance_cents,
                       balanceText: b.balance_cents < 0 ? self.t("sum.they_owe", { amount: self.money(-b.balance_cents) }) : b.balance_cents > 0 ? self.t("sum.you_hold", { amount: self.money(b.balance_cents) }) : self.t("sum.even") };
            }).concat((X.peopleOwed(S.state.entries, st, upTo) || []).filter(function (p) { return !p.funder && p.owed_cents > 0; }).map(function (p, i) {
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
        // The period's giveaways (GVX.giveawayLedger; the period is the one Entries and Summary use): what
        // was on hand at its start, what came in and went out, what is on hand at its end — per item, and
        // in all (also per magazine).
        gl: function () {
          var r = this.range();
          return this.memo("gl", r.from + "|" + r.to, function () { return S.X.giveawayLedger(S.state.entries, r); }) || { items: [], totals: {} };
        },
        // the "At the start" column: only a period with a first day has something before it
        hasStart: function () { return !!this.range().from; },
        // …and it is shown only when some item had something on hand then (a column of zeros says nothing)
        anyStart: function () { return this.hasStart() && this.inv().some(function (x) { return x.startN !== 0; }); },
        inv: function () {
          var self = this, r = this.range();
          return this.memo("inv", r.from + "|" + r.to, function () {
            return (this.gl().items || []).map(function (x) {
              // the core's own item key (x-for's key): accents make two items ("La Viña" / "La Vina"),
              // so norm() — which drops them — would give two rows one key, and one would not show
              return { key: x.key || (norm(x.item) + "|" + (x.format || "")), item: x.item || self.t("give.no_item"), format: x.format || "", formatText: x.format ? self.t("format." + x.format) : "",
                       start: self.count(x.start || 0), startN: x.start || 0, bought: self.count(x.bought_qty || 0), received: self.count(x.received_qty || 0), given: self.count(x.given_qty || 0),
                       onHand: x.on_hand || 0, onHandText: self.count(x.on_hand || 0), avg: x.avg_unit_cents ? self.money(x.avg_unit_cents) : "—",
                       hasAvg: !!x.avg_unit_cents, cost: self.money(x.cost_cents || 0) };
            }).sort(function (a, b) { return a.item.localeCompare(b.item); });
          }) || [];
        },
        // the tiles over the list: given away, bought and received in the period (Grapevine · La Viña), on hand at its end
        giveTiles: function () {
          var self = this, t = this.gl().totals || {}, f = t.by_format || {};
          var split = function (k) {
            var gv = f.gv ? f.gv[k] : 0, lv = f.lv ? f.lv[k] : 0;
            return gv || lv ? self.t("give.split", { gv: self.count(gv), lv: self.count(lv) }) : "";
          };
          return [
            { id: "given", icon: "heart-handshake", tone: "xp-tone-rose", label: this.t("give.t_given"), value: this.count(t.given || 0), note: split("given") },
            { id: "bought", icon: "gift", tone: "xp-tone-vine", label: this.t("give.t_bought"), value: this.count(t.bought || 0),
              note: t.cost_cents ? this.t("give.t_cost", { amount: this.money(t.cost_cents) }) : split("bought") },
            { id: "received", icon: "package", tone: "xp-tone-teal", label: this.t("give.t_received"), value: this.count(t.received || 0), note: split("received") },
            { id: "on_hand", icon: "library", tone: "xp-tone-gv", label: this.t("give.t_on_hand"), value: this.count(t.on_hand || 0),
              note: this.hasStart() && t.start ? this.t("give.t_start", { n: this.count(t.start) }) : split("on_hand") },
          ];
        },
        giveEvents: function () {
          var self = this, range = this.range();
          return this.memo("giveEv", range.from + "|" + range.to, function () {
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
        // anything ever recorded, whatever the period: an empty list then says "in this period", not "yet"
        everLit: function () {
          return !!this.memo("everLit", "", function () {
            return S.state.entries.some(function (e) { return e.type === "giveaway" || e.type === "stock" || (e.type === "expense" && e.giveaway); });
          });
        },
        everGiven: function () {
          return !!this.memo("everGiven", "", function () { return S.state.entries.some(function (e) { return e.type === "giveaway"; }); });
        },
        // the items to suggest: every one ever given or kept to give (whatever the period), then the rest typed before
        itemSuggest: function () {
          return this.memo("itemSug", "", function () {
            return uniq((S.X.inventory(S.state.entries) || []).map(function (x) { return x.item; }).concat(this.suggest("item")));
          }) || [];
        },

        /* ================= Subscriptions (in the Giveaways view) ================= */
        // Every subscription and where it stands today (GVX.subscriptions: ending soon, ended, active,
        // renewed, no end date), the reminder setting deciding "soon".
        subsAll: function () {
          var days = this.st().renewal_days || 60;
          return this.memo("subs", String(days), function () { return S.X.subscriptions(S.state.entries, this.st(), today(), days) || []; }) || [];
        },
        // the list on screen: the status and kind chosen above it
        subRows: function () {
          var self = this, f = this.subF;
          return this.memo("subRows", f.status + "|" + f.kind, function () {
            return this.subsAll().filter(function (s) { return (!f.status || s.status === f.status) && (!f.kind || s.kind === f.kind); }).map(function (s) {
              var left = s.days_left;
              // whom it is for: the name typed — or, for your own and the group's (no name expected), those words;
              // "No name given" is left for a gift typed without one
              var who = clean(s.person) || self.t(s.kind === "self" ? "subs.who_self" : s.kind === "group" ? "subs.who_group" : "subs.no_person");
              return { id: s.id, who: who, what: s.product ? self.t("sub_product." + s.product) : self.t("subs.no_product"), n: s.qty || 1,
                       kind: s.kind ? self.t("sub_kind." + s.kind) : "", qty: s.qty > 1 ? self.t("list.subs_qty", { n: self.count(s.qty) }) : "",
                       start: s.start ? self.day(s.start, "mid") : "—", end: s.end ? self.day(s.end, "mid") : "—",
                       status: s.status, statusText: self.t("subs.st_" + s.status), icon: SUB_ICON[s.status] || "clock",
                       // how soon, in words: "in 45 days", "122 days ago", "starts Oct 20, 2026"
                       when: s.status === "ending" ? (left === 0 ? self.t("subs.ends_today") : self.plural(left, "subs.ends_in_one", "subs.ends_in"))
                         : s.status === "ended" ? self.plural(-left, "subs.ended_ago_one", "subs.ended_ago")
                         : s.upcoming ? self.t("subs.starts", { date: self.day(s.start, "mid") }) : "",
                       canRenew: s.status !== "renewed" && !!s.end };
            });
          }) || [];
        },
        // how many subscriptions (10 gifts bought at once are 10, as on the tiles), not how many rows
        subStatusCount: function (status) {
          return this.subsAll().reduce(function (n, s) { return n + (!status || s.status === status ? s.qty || 1 : 0); }, 0);
        },
        // …and in the list as it is filtered (the line above it)
        subShown: function () { return this.subRows().reduce(function (n, s) { return n + s.n; }, 0); },
        subToggle: function (status) { this.subF.status = this.subF.status === status ? "" : status; },
        // the tiles: given in the period (Grapevine · La Viña), and today: running, ending soon, ended without a renewal
        subTiles: function () {
          var self = this, r = this.range();
          var c = this.memo("subCounts", r.from + "|" + r.to, function () { return S.X.subscriptionCounts(this.subsAll(), r); }) || {};
          var gm = c.gifted_by_magazine || {};
          return [
            { id: "gifted", icon: "gift", tone: "xp-tone-lv", label: this.t("subs.t_gifted"), value: this.count(c.gifted || 0),
              note: gm.gv || gm.lv ? this.t("give.split", { gv: this.count(gm.gv || 0), lv: this.count(gm.lv || 0) }) : this.plural(c.bought || 0, "subs.t_bought_one", "subs.t_bought") },
            { id: "running", icon: "newspaper", tone: "xp-tone-vine", label: this.t("subs.t_running"), value: this.count(c.running || 0), note: this.t("subs.t_today") },
            { id: "ending", icon: "calendar", tone: "xp-tone-gold", label: this.t("subs.t_ending"), value: this.count(c.ending || 0),
              note: this.t("subs.t_within", { n: this.count(this.st().renewal_days || 60) }) },
            { id: "ended", icon: "bell", tone: "xp-tone-rose", label: this.t("subs.t_ended"), value: this.count(c.ended || 0), note: this.t("subs.t_not_renewed") },
          ];
        },
        // The end dates of the subscriptions still to renew, as a calendar file for the visitor's own calendar
        // (GVX.subscriptionsICS: an alarm the reminder setting's days before each end, tomorrow at the latest).
        // It is handed every subscription: the renewed ones tell it which event a renewal moves. Made here;
        // saved where the visitor saves it — nothing is uploaded.
        subsIcs: function () {
          var all = this.subsAll();
          if (!all.some(function (s) { return (s.status === "ending" || s.status === "active") && s.end; })) { this.say(this.t("subs.ics_none")); return; }
          var href = String(location.href || "");
          var text = S.X.subscriptionsICS(all, { days: this.st().renewal_days || 60, lang: this.L, strings: S.ui, url: href ? href.split("#")[0] + "#giveaways" : "", now: new Date() });
          var name = this.t("data.file_base") + "-" + safeName(this.t("subs.ics_word")) + "-" + today() + ".ics";
          saveBlob(new Blob([text], { type: "text/calendar;charset=utf-8" }), name);
          this.say(this.t("toast.downloaded", { file: name }));
        },

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
            // a line that stands for several trips says so (352.2 mi = 3 round trips to the convention) — once:
            // a trip with no event has the core's words for it, which say it already
            var n = Number(l.trips) || 1, trips = n > 1 ? self.t(l.round_trip ? "list.trips_round" : "list.trips", { n: self.count(n) }) : "";
            var purpose = l.description || l.purpose || "";
            return { i: i, date: self.day(l.date, "mid"), route: clean(l.from) + (l.to ? " → " + clean(l.to) : ""),
                     purpose: [purpose, trips && purpose.indexOf(trips) === -1 ? trips : ""].filter(Boolean).join(" · "),
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
          var name = this.t("data.file_base") + "-" + safeName(this.t("data.request_word")) + "-" + (safeName(this.funderName(this.rq.funder)) || "x") + "-" + today() + ".csv";
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

        /* ---- the service report: what your service cost, set out as a GVR's own expense report does it
           (GVX.serviceReport) — for your records, your district or the next GVR; a record, not a request ---- */
        years: function () {
          this.rev;
          var ys = {}, y = new Date().getFullYear();
          ys[y] = 1;
          S.state.entries.forEach(function (e) { var k = String(e.date || "").slice(0, 4); if (/^\d{4}$/.test(k)) ys[k] = 1; });
          return Object.keys(ys).map(Number).sort(function (a, b) { return b - a; });
        },
        // its periods: each year with entries (the newest first), the service panels, all dates, your own dates
        rpPeriods: function () {
          var self = this, out = this.years().map(function (y) { return { id: "y:" + y, label: String(y) }; });
          this.panels().forEach(function (p) { out.push({ id: "panel:" + p.id, label: self.t("period.panel", { n: p.id }) }); });
          out.push({ id: "all", label: this.t("period.all") }, { id: "custom", label: this.t("period.custom") });
          return out;
        },
        rpRange: function () {
          var m = /^y:(\d{4})$/.exec(this.rp.period);
          return m ? { from: m[1] + "-01-01", to: m[1] + "-12-31" } : periodRange(this.rp.period, this.panels(), this.rp.from, this.rp.to);
        },
        rep: function () {
          var r = this.rpRange(), rp = this.rp;
          return this.memo("rep", [r.from, r.to, !!rp.names, !!rp.notes, this.L].join("|"), function () {
            return S.X.serviceReport(S.state.entries, this.st(), { from: r.from, to: r.to, lang: this.L, strings: S.ui, includeNames: !!rp.names,
              includeNotes: !!rp.notes, today: today() });
          }) || { header: {}, rows: [], money: [], miles: [], totals: {}, giveaways: {}, subscriptions: {} };
        },
        // a date, or a stay / a trip over several days: "Mar 20 – Mar 22, 2026" (the year once when it is the same).
        // A date keeps its words together (no-break spaces: never "Jul / 18, / 2026" in a narrow column); a
        // range breaks at its dash
        days: function (a, b) {
          if (!a) return "";
          var nb = function (s) { return String(s).replace(/ /g, "\u00a0"); };
          if (!(b && b > a)) return nb(this.day(a, "mid"));
          var first = a.slice(0, 4) === b.slice(0, 4) ? fmtDay(a, "short", this.L) : "";
          return nb(first || this.day(a, "mid")) + " – " + nb(this.day(b, "mid"));
        },
        // what the report says, ready for the screen and the paper
        rpView: function () {
          var self = this, r = this.rpRange(), rp = this.rp;
          return this.memo("rpView", [r.from, r.to, !!rp.names, !!rp.notes, this.L].join("|"), function () {
            var R = this.rep(), t = R.totals || {}, g = R.giveaways || {}, sc = R.subscriptions || {}, h = R.header || {};
            var mi = function (n) { return self.t("list.miles", { n: self.count(n || 0) }); };
            var bf = g.by_format || {}, bm = sc.by_magazine || {};
            return {
              empty: !(R.rows || []).some(function (x) { return x.kind !== "total"; }),
              period: h.first ? this.days(h.first, h.last) : this.rpPeriodLabel(),
              rates: (h.rates || []).map(function (x) { return self.t("form.rate_value", { rate: x }); }).join(" · "),
              rows: (R.rows || []).map(function (x, i) {
                return { key: i, kind: x.kind, label: x.label, miles: x.kind === "miles" || x.kind === "miles_total" ? mi(x.miles) : "",
                         trips: x.trips ? self.plural(x.trips, "sum.trips_one", "sum.trips") : "", amount: self.money(x.cents) };
              }),
              money: (R.money || []).map(function (s) {
                return { key: s.id, label: s.label, total: self.money(s.cents), lines: s.lines.map(function (l) {
                  return { key: l.id, dates: self.days(l.date, l.end_date), what: l.description, event: l.event && norm(l.description).indexOf(norm(l.event)) === -1 ? l.event : "",
                           where: [l.vendor, l.place].filter(Boolean).join(", "), paid: [l.method, l.ref].filter(Boolean).join(" · "), amount: self.money(l.amount_cents), notes: l.notes };
                }) };
              }),
              miles: (R.miles || []).map(function (s) {
                return { key: s.id || "-", label: s.label, total: self.money(s.cents), miles: mi(s.miles), trips: self.plural(s.trips, "sum.trips_one", "sum.trips"),
                         lines: s.lines.map(function (l) {
                  var route = [l.from, l.to].filter(Boolean).join(" → "), what = l.event || l.description || route;
                  // how the miles were worked out, for the phone's line under the event: "3 round trips · 58.7 mi
                  // one way" (the one-way miles exact: they multiply back to the miles beside them)
                  var n = Number(l.trips) || 1, ow = l.one_way === "" ? "" : self.oneWayText(l.one_way);
                  var tripLine = l.no_miles || !ow ? "" : n > 1 ? self.t(l.round_trip ? "rep.line_round_trips" : "rep.line_trips", { n: self.count(n), mi: ow })
                    : l.round_trip ? self.t("rep.line_round_trip", { mi: ow }) : "";
                  return { key: l.id, dates: self.days(l.date, l.end_date), what: what, route: l.no_miles ? l.ride : route === what ? "" : route, role: l.role,
                           trips: l.no_miles ? "—" : self.count(l.trips), oneWay: ow || "—", miles: self.count(l.miles), tripLine: tripLine,
                           milesText: l.no_miles ? "" : mi(l.miles),
                           amount: self.money(l.amount_cents), notes: l.notes, rode: l.no_miles };
                }) };
              }),
              // who covers it: your own contribution, what you asked back, what came back, what is still owed
              totals: [
                { key: "self", label: this.t("rep.self"), value: this.money(t.self_cents) },
                { key: "asked", label: this.t("rep.asked"), value: this.money(t.claimable_cents) },
                { key: "received", label: this.t("sum.received"), value: this.money(t.received_cents) },
                { key: "owed", label: this.t("sum.owed"), value: this.money(t.owed_cents) },
              ],
              hasGiven: !!g.given,
              given: { total: this.count(g.given || 0), split: bf.gv || bf.lv ? this.t("give.split", { gv: this.count(bf.gv ? bf.gv.given : 0), lv: this.count(bf.lv ? bf.lv.given : 0) }) : "",
                       events: (g.events || []).map(function (x, i) { return { key: i, name: x.event || self.t("give.no_event"), n: self.count(x.total_qty) }; }) },
              // the subscriptions bought in the period: in all (Grapevine · La Viña), then by kind (only the kinds there are)
              hasSubs: !!sc.bought,
              subsTotal: this.count(sc.bought || 0),
              subsSplit: bm.gv || bm.lv ? this.t("give.split", { gv: this.count(bm.gv || 0), lv: this.count(bm.lv || 0) }) : "",
              subs: ["gift", "helped", "group", "self"].filter(function (k) { return (sc.by_kind || {})[k]; }).map(function (k) { return { key: k, label: self.t("sub_kind." + k), n: self.count(sc.by_kind[k]) }; }),
            };
          }) || { rows: [], money: [], miles: [], totals: [], given: { events: [] }, subs: [], empty: true };
        },
        // the period's name: "2026", "Panel 77", "All dates", or the dates chosen
        rpPeriodLabel: function () {
          var self = this, p = this.rp.period, hit = this.rpPeriods().filter(function (x) { return x.id === p; })[0], r = this.rpRange();
          if (p === "custom") return r.from || r.to ? this.t("req.dates", { from: r.from ? self.day(r.from, true) : "…", to: r.to ? self.day(r.to, true) : "…" }) : this.t("req.all_dates");
          return hit ? hit.label : "";
        },
        // "Prepared for" and the note at the top: the visitor's own words, kept with the settings
        repField: function (k) { this.rev; return (this.st().report || {})[k] || ""; },
        setReport: function (k, v) {
          var s = this.st();
          s.report = s.report || {};
          s.report[k] = k === "note" ? String(v || "").replace(/\r\n?/g, "\n").trim().slice(0, 2000) : clean(v).slice(0, 120);
          this.save();
        },
        rpPrint: function () { this.printPart("report", this.t("rep.doc_title") + " — " + this.rpPeriodLabel()); },
        // the report's lines as a CSV (GVX.reportCSV): names and notes as the report shows them
        rpCsv: function () {
          var R = this.rep();
          if (!(R.money || []).length && !(R.miles || []).length) { this.say(this.t("toast.nothing_to_export")); return; }
          var name = this.t("data.file_base") + "-" + safeName(this.t("rep.word")) + "-" + (safeName(this.rpPeriodLabel()) || "x") + "-" + today() + ".csv";
          saveBlob(new Blob([S.X.reportCSV(R, S.ui, this.L)], { type: "text/csv;charset=utf-8" }), name);
          this.say(this.t("toast.downloaded", { file: name }));
        },

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
        // the receipt photos the ledger's entries point to, kept on this device: [{id, rec, entry}], by date
        backupPhotos: function () {
          var byId = {};
          S.state.entries.forEach(function (e) { if (e.receipt === "photo") byId[e.id] = e; });
          return photos.all().then(function (recs) {
            return (recs || []).filter(function (r) { return r && r.blob && byId[r.id]; }).map(function (r) { return { id: r.id, rec: r, entry: byId[r.id] }; })
              .sort(function (a, b) { return a.entry.date < b.entry.date ? -1 : a.entry.date > b.entry.date ? 1 : a.id < b.id ? -1 : 1; });
          });
        },
        // How big the backups will be, before they are made (Settings → Data says it, and a big one is
        // asked about): the ledger, plus each photo as it is kept (the .zip stores them as they are).
        measureBackup: function () {
          var self = this, plain = 0;
          try { plain = JSON.stringify(S.state).length + 300; } catch (e) { plain = 0; }
          return this.backupPhotos().then(function (list) {
            var bytes = plain;
            list.forEach(function (p) { bytes += (p.rec.blob.size || 0) + 2 * (S.X.receiptFile(p.entry, p.rec.type).length + 46) + 200; });
            self.bk = { ready: true, photos: list.length, bytes: bytes, plain: plain };
            return self.bk;
          }, function () { self.bk = { ready: true, photos: 0, bytes: plain, plain: plain }; return self.bk; });
        },
        sizeText: function (bytes) { var p = sizeParts(bytes); return this.t(p.key, { n: this.count(p.n) }); },
        photosText: function (n) { return n ? this.plural(n, "data.photos_one", "data.photos") : this.t("data.photos_none"); },
        bkLine: function () {
          var b = this.bk;
          return b.ready ? this.t("data.size_full", { size: this.sizeText(b.bytes), photos: this.photosText(b.photos) }) + " " +
            this.t("data.size_plain", { size: this.sizeText(b.plain) }) : "";
        },
        bkBig: function () { return this.bk.ready && this.bk.bytes > BIG_BACKUP; },
        /* "Back up now" / "Full backup": entries, settings and every receipt photo, in one .zip — the ledger
           as backup.json and each photo a file of its own (GVF.zip, nothing compressed, read back in slices),
           so even hundreds of photos restore. A big one is asked about first (too big for most e-mail): save
           it anyway, or back up without photos. how "plain": the .json of the ledger alone ("Back up without
           photos": the photos stay on this device). */
        exportBackup: function (how) {
          var self = this;
          if (!S.state.entries.length) { this.say(this.t("toast.nothing_to_export")); return Promise.resolve(); }
          if (how === "plain") { this.saveBackup(new Blob([S.X.toBackup(S.state, [])], { type: "application/json" }), "-" + safeName(this.t("data.no_photos_word")), ".json"); return Promise.resolve(); }
          return this.measureBackup().then(function (b) {
            if (b.bytes <= BIG_BACKUP) return true;
            return self.confirm(self.t("ask.backup_big", { size: self.sizeText(b.bytes), photos: self.photosText(b.photos) }), self.t("ask.backup_big_ok"), false, self.t("ask.backup_big_alt"));
          }).then(function (yes) {
            if (yes === "alt") return self.exportBackup("plain");
            if (!yes) return;
            self.say(self.t("toast.preparing"));
            return self.backupPhotos().then(function (list) {
              var G = window.GVF;
              if (!G) return self.backupJson(list);      // (no zip helper: the photos inside the .json, as before 1.2.0)
              var files = [], receipts = [];
              list.forEach(function (p) {
                var name = S.X.receiptFile(p.entry, p.rec.type);
                files.push({ name: name, data: p.rec.blob });
                receipts.push({ id: p.id, type: p.rec.type || "image/jpeg", file: name, name: p.rec.name || "", added: p.rec.added || "", w: p.rec.w, h: p.rec.h });
              });
              files.unshift({ name: "backup.json", data: S.X.toBackup(S.state, receipts) });
              return G.zip(files, new Date()).then(function (blob) { self.saveBackup(blob, "", ".zip"); });
            });
          }).catch(function (e) { if (window.console) console.error("[expenses]", e); self.say(self.t("toast.backup_failed")); });
        },
        // the photos inside the .json as data: URLs (the full backup of 1.1.0: when the zip helper is missing)
        backupJson: function (list) {
          var self = this;
          return Promise.all(list.map(function (p) { return blobToDataUrl(p.rec.blob).then(function (u) { return { id: p.id, type: p.rec.type || "image/jpeg", dataUrl: u }; }); }))
            .then(function (receipts) { self.saveBackup(new Blob([S.X.toBackup(S.state, receipts)], { type: "application/json" }), "", ".json"); });
        },
        saveBackup: function (blob, what, ext) {
          var name = this.t("data.file_base") + "-" + this.t("data.backup_word") + what + "-" + today() + ext;
          saveBlob(blob, name);
          this.stamp("lastBackup");
          this.save();
          this.say(this.t("toast.backup_done", { file: name, size: this.sizeText(blob.size) }));
        },
        // the entries that have a photo (and the ones a pending "Undo" would bring back — this tab's, or
        // another's that has not run out)
        photoIds: function () {
          var ids = undoPending();
          S.state.entries.forEach(function (e) { if (e.receipt === "photo") ids[e.id] = 1; });
          if (S.undo) S.undo.photoIds.forEach(function (id) { ids[id] = 1; });
          return ids;
        },
        // Photos no entry points to any more are deleted: a delete whose undo time never ran out (the
        // page was closed), an import that replaced everything. A deleted receipt never travels on in a
        // backup.
        cleanPhotos: function () {
          var self = this, mine = this.photoIds();
          return photos.keys().then(function (keys) {
            return self.dropPhotos((keys || []).filter(function (k) { return !mine[k]; }));
          }).catch(function () {});
        },
        lastBackupText: function () { this.rev; return this.ago(S.state && S.state.meta ? S.state.meta.lastBackup : null); },
        storageKb: function () { this.rev; var raw = lsGet(KEY); return raw ? Math.max(1, Math.round(raw.length * 2 / 1024)) : 0; },
        usageText: function () { return this.usage == null || this.usage < 512000 ? "" : this.t("data.usage", { mb: (Math.round(this.usage / 104857.6) / 10).toLocaleString(this.L === "es" ? "es-US" : "en-US") }); },

        /* ================= import: a CSV, an Excel workbook or a backup → preview → merge or replace ================= */
        impReset: function () { S.impRows = null; S.impPlan = null; S.impBackup = null; this.imp = { step: "pick", err: "", name: "" }; this.dragOver = false; },
        impDrop: function (ev) {
          this.dragOver = false;
          var files = ev.dataTransfer && ev.dataTransfer.files;
          if (files && files.length) this.impFiles(files);
        },
        impPick: function (ev) { var files = Array.prototype.slice.call(ev.target.files || []); ev.target.value = ""; if (files.length) this.impFiles(files); },
        // Several files at once: a backup that was unpacked (a computer may open a .zip by itself) — its
        // backup.json with its photos. The one that is not a photo is the file; the photos go with it.
        impFiles: function (list) {
          var files = Array.prototype.slice.call(list || []).filter(Boolean), pic = /\.(jpe?g|png|webp|gif)$/i;
          var main = files.filter(function (f) { return !pic.test(f.name || ""); })[0] || files[0], pics = {};
          files.forEach(function (f) { if (f !== main && pic.test(f.name || "")) pics[f.name] = f; });
          return this.impFile(main, pics);
        },
        /* What the file is decides how it is read (GVX.importKind, from its first bytes): a .zip — the full
           backup, or an Excel workbook (.xlsx) —, Excel's older .xls (asked for as .xlsx or CSV), a .json
           backup, or a CSV (UTF-8, UTF-16 or Windows-1252: GVX.decodeText). A CSV may weigh up to 10 MB; a
           backup is the visitor's own and has no limit that matters (it is read in slices). */
        impFile: function (file, pics) {
          var self = this, X = S.X;
          this.impReset();
          this.imp.name = file.name;
          var tooBig = function (limit) { self.imp.err = self.t("imp.too_big", { mb: self.count(Math.round(limit / 1048576)) }); };
          return sniff(file).then(function (head) {
            var kind = X.importKind(file.name, String(head.text || "").replace(/^﻿/, ""), head.bytes), limit = X.importLimit(kind);
            if (file.size > limit) return tooBig(limit);
            if (kind === "xls") { self.imp.err = self.msgKey("expenses.err.xls_old"); return; }
            if (kind === "zip") return self.impZip(file, pics || {});
            if (kind === "backup") return self.impBackupFile(file, pics || {});
            return readText(file).then(function (text) { self.impCsvText(String(text || "").replace(/^﻿/, "")); });
          }).catch(function (e) {
            if (window.console) console.error("[expenses]", e);
            self.imp.err = e && e.key ? self.msgKey(e.key) : self.t("imp.unreadable");
          });
        },
        // a .zip: the full backup (backup.json and its photos — or any one .json someone zipped), or an Excel workbook
        impZip: function (file, pics) {
          var self = this, X = S.X, G = window.GVF;
          if (!G) { this.imp.err = this.t("imp.unreadable"); return Promise.resolve(); }
          return G.readZip(file).then(function (zip) {
            if (zip.has("xl/workbook.xml")) return G.xlsxRows(zip, { maxRows: X.LIMITS.rows + 1 }).then(function (rows) { self.impCsvRows(rows, "xlsx"); });
            var jsons = zip.entries.filter(function (e) { return /^[^/]+\.json$/i.test(e.name); });
            var main = zip.has("backup.json") ? "backup.json" : jsons.length === 1 ? jsons[0].name : "";
            if (!main) { self.imp.err = self.msgKey("expenses.err.backup_foreign"); return; }
            return zip.text(main, X.LIMITS.json).then(function (text) { self.impBackupRead(X.readBackup(text, S.cfg), null, pics, zip); });
          });
        },
        // a .json backup: a small one read whole; a big one (its photos inside, as before 1.2.0) in slices
        // (GVF.jsonBackup), each photo read only when it is restored — unless it is not laid out as the
        // tracker writes it (then whole, up to GVX.LIMITS.json)
        impBackupFile: function (file, pics) {
          var self = this, X = S.X, G = window.GVF;
          var whole = function () {
            if (file.size > X.LIMITS.json) { self.imp.err = self.t("imp.too_big", { mb: self.count(Math.round(X.LIMITS.json / 1048576)) }); return; }
            return readText(file).then(function (t) { self.impBackupText(t, pics); });
          };
          if (file.size <= X.LIMITS.bytes || !G || !file.slice) return whole();
          return G.jsonBackup(file).then(function (jb) { return jb ? self.impBackupRead(X.readBackup(jb.head, S.cfg), jb.receipts, pics) : whole(); });
        },
        impCsvText: function (text) {
          if (!clean(text)) { this.imp.err = this.t("imp.empty"); return; }
          this.impCsvRows(S.X.parseCSV(text), "csv");
        },
        // the rows of a CSV or of an Excel sheet → the preview (or the mapping step)
        impCsvRows: function (rows, from) {
          if (rows && rows.error) { this.imp.err = this.msgKey(rows.error); return; }
          if (!rows || !rows.length) { this.imp.err = this.t("imp.empty"); return; }
          S.impRows = rows;
          this.imp.from = from || "csv";
          this.imp.kind = "csv";
          this.imp.opts = { dateOrder: this.L === "es" ? "dmy" : "mdy", decimal: "auto", includeDuplicates: false, positive: "" };
          this.imp.map = { date: "", description: "", amount: "", category: "", miles: "", notes: "" };
          this.imp.mapped = false;
          this.imp.forceMap = false;
          this.imp.mode = "merge";
          this.impPlan();
        },
        // "Map the columns myself": a file that looked like the tracker's own goes through the mapping step
        impMapMyself: function () { this.imp.forceMap = true; this.imp.mapped = false; this.imp.opts.positive = ""; this.impPlan(); },
        impPlan: function () {
          var X = S.X, im = this.imp, o = { dateOrder: im.opts.dateOrder, allowDuplicates: !!im.opts.includeDuplicates, lang: this.L, forceMapping: !!im.forceMap };
          if (im.opts.decimal !== "auto") o.decimal = im.opts.decimal;
          if (im.opts.positive) o.positive = im.opts.positive;
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
        // (a new mapping: the core guesses again which sign is spending — the amount column may have changed)
        impUseMap: function () { this.imp.mapped = true; this.imp.opts.positive = ""; this.impPlan(); },
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
          // somebody else's sheet with positive amounts: the preview asks what they are (the core's guess
          // is the starting answer, so the select shows what the rows below were read as)
          this.imp.signs = plan.format === "mapped" && plan.signs && plan.signs.positive ? plan.signs : null;
          if (plan.positive) this.imp.opts.positive = plan.positive;
          // …and the date order the rows were read in (the file's own, when its dates show one)
          if (plan.dateOrder) this.imp.opts.dateOrder = plan.dateOrder;
          this.imp.newCats = (plan.newCategories || []).map(function (c) { return self.lbl(c.label || c.name || c); });
          this.imp.newFunders = (plan.newFunders || []).map(function (c) { return self.lbl(c.name || c.label || c); });
          this.imp.newActs = (plan.newActivities || []).map(function (c) { return self.lbl(c.name || c.label || c); });
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
        impBackupText: function (text, pics) {
          var r;
          try { r = S.X.readBackup(text, S.cfg); } catch (e) { r = { ok: false, error: "expenses.err.backup_invalid" }; }
          this.impBackupRead(r, null, pics);
        },
        /* A backup read (GVX.readBackup's answer r) → the preview. Its photos, each as a source to read when
           it is restored: lazy (a big .json's, GVF.jsonBackup), a data: URL inside the .json, a file of the
           .zip (zip), or one of the photos picked with an unpacked backup.json (pics, by name). A photo the
           backup names but nothing holds is counted as missing (the preview says how to bring it along). */
        impBackupRead: function (r, lazy, pics, zip) {
          if (!r || !r.ok) { this.imp.err = this.msgKey((r && r.error) || "expenses.err.backup_invalid"); return; }
          var st = r.state || {}, list = [], missing = 0;
          (lazy || r.receipts || []).forEach(function (x) {
            if (!x || !x.id) return;
            var meta = { id: x.id, type: x.type || "image/jpeg", w: x.w || 0, h: x.h || 0, name: x.name || "", added: x.added || "" };
            if (typeof x.load === "function") meta.load = x.load;
            else if (x.dataUrl) meta.load = function () { return Promise.resolve(dataUrlToBlob(x.dataUrl)); };
            else if (x.file && zip && zip.has(x.file)) meta.load = function () { return zip.blob(x.file, meta.type); };
            else if (x.file && pics && Object.prototype.hasOwnProperty.call(pics, x.file)) meta.load = function () { return Promise.resolve(pics[x.file]); };
            if (meta.load) list.push(meta); else missing++;
          });
          S.impBackup = { entries: st.entries || [], settings: st.settings || null, receipts: list, meta: st.meta || null };
          this.imp.kind = "backup";
          this.imp.mode = "merge";
          this.imp.counts = { entries: S.impBackup.entries.length, photos: list.length, missing: missing };
          this.imp.step = "backup";
        },
        impApply: function () {
          var self = this, im = this.imp, n = S.state.entries.length;
          var go = function () { return im.kind === "backup" ? self.impApplyBackup() : self.impApplyCsv(); };
          if (im.mode === "replace" && n) {
            return this.confirm(this.t("ask.replace", { n: this.count(n) }), this.t("ask.replace_ok"), true).then(function (yes) { return yes ? go() : null; });
          }
          return Promise.resolve(go());
        },
        impApplyCsv: function () {
          var X = S.X, plan = S.impPlan, before = S.state.entries.length;
          var next = X.applyImport(S.state, plan, { mode: this.imp.mode });
          if (!next || !Array.isArray(next.entries)) { this.imp.err = this.t("imp.unreadable"); return; }
          next.settings = X.mergeDefaults(S.cfg, next.settings || S.state.settings);
          next.meta = next.meta || S.state.meta;
          S.state = next;
          var stored = this.save();
          // the replaced entries' receipt photos go too — once the new ledger is kept: a save the
          // browser refused leaves the old ledger stored, and it still points to them
          if (stored && this.imp.mode === "replace") this.cleanPhotos();
          var added = this.imp.mode === "replace" ? next.entries.length : Math.max(0, next.entries.length - before);
          // "Done" and the toast count what the Import button counted: the new entries AND the updated ones (a merge
          // that only updated entries said "0 entries imported"), as a backup restore counts the entries it touched
          var updated = this.imp.mode === "replace" ? 0 : (plan.update || []).length;
          this.imp = { step: "done", added: added, updated: updated, err: "" };
          this.saySaved(this.plural(added + updated, "toast.imported_one", "toast.imported"));
          if (next.entries.length) this.askPersist();
        },
        // A full backup: replace, or merge by id (the newer copy of an entry wins; new list items are added).
        impApplyBackup: function () {
          var self = this, X = S.X, b = S.impBackup, mode = this.imp.mode, st = S.state, now = nowIso();
          var settings = mode === "replace" && b.settings ? X.mergeDefaults(S.cfg, b.settings) : st.settings;
          if (mode !== "replace" && b.settings) {
            ["categories", "funders", "methods", "activities", "rates", "budgets", "custom_fields"].forEach(function (k) {
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
          var added = Object.keys(touched).length, want = {};
          entries.forEach(function (e) { if (e.receipt === "photo") want[e.id] = 1; });
          S.state = { v: st.v || 1, entries: entries, settings: settings, meta: Object.assign({}, st.meta || {}, { lastBackup: (b.meta && b.meta.lastBackup) || st.meta.lastBackup }) };
          var stored = this.save();
          this.imp = { step: "done", added: added, updated: 0, err: "", photos: 0, photosDone: 0, photoErrs: 0 };
          this.saySaved(this.plural(added, "toast.imported_one", "toast.imported"));
          if (entries.length) this.askPersist();
          // the backup's photo of each entry that points to one: the entries taken from the backup, and any
          // entry this device has no photo for (its copy came from a CSV: the same entry, no photo) — one
          // at a time, a breath between them (hundreds restore without freezing the page; the "done" step
          // counts them). "replace" then deletes the old photos — once the restored ledger is kept (a
          // refused save leaves the old ledger stored, pointing to them) — and the photos of entries the
          // backup has as well stay until their own arrives.
          var im = this.imp;
          S.restoring = true;
          this.armLeave();
          return photos.keys().then(function (have) {
            var got = {};
            (have || []).forEach(function (k) { got[k] = 1; });
            var todo = (b.receipts || []).filter(function (r) { return r && want[r.id] && (touched[r.id] || !got[r.id]); });
            im.photos = todo.length;
            return todo.reduce(function (p, r) {
              return p.then(function () { return r.load(); }).then(function (blob) {
                if (!blob) throw new Error("photo");
                return photos.put({ id: r.id, type: blob.type || r.type || "image/jpeg", blob: blob, w: r.w || 0, h: r.h || 0, name: r.name || "", added: r.added || now });
              }).then(function () { im.photosDone++; }, function () { im.photoErrs++; }).then(breathe);
            }, Promise.resolve());
          }).then(function () { return mode === "replace" && stored ? self.cleanPhotos() : null; }).catch(function () {}).then(function () {
            S.restoring = false;
            self.armLeave();
          });
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
            ids.forEach(function (id) { delete self.sel[id]; });
            if (self.save()) self.dropPhotos(ids);
            self.saySaved(self.t("toast.examples_removed"));
          });
        },
        eraseReady: function () { return clean(this.eraseText).toUpperCase() === this.t("data.erase_word").toUpperCase(); },
        eraseAll: function () {
          var self = this;
          if (!this.eraseReady()) return;
          this.confirm(this.t("ask.erase"), this.t("ask.erase_ok"), true).then(function (yes) {
            if (!yes) return;
            // (a ledger that could not be read and could not be kept aside stays, with its photos: its
            // notice offers it first)
            if (self.lock !== "unreadable") { lsDel(KEY); self.lock = ""; photos.clear(); }
            lsDel(UNDO_KEY);
            S.undo = null;
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
          return kind === "categories" || kind === "funders" || kind === "methods" || kind === "activities" ? l.sort(this.byOrder) : l;
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
        field: { categories: "category", funders: "funder", methods: "method", activities: "activity" },
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
        addActivity: function () {
          var s = this.st(), id = S.X.newId();
          s.activities = s.activities || [];
          s.activities.push({ id: id, name: this.t("set.new_activity"), builtin: false, hidden: false, order: this.nextOrder("activities") });
          this.save();
          this.focusSoon("xp-s-act-" + id);
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
