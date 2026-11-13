/* Area script — Read / Share Your Story / Subscribe / GVR-RLV Corner / About.
   Loaded (defer) after app.js and before Alpine, so components registered on
   "alpine:init" are ready when Alpine starts. No build step, no dependencies.
   All user-visible strings come from the page (data-* attributes rendered from
   src/_i18n/read.json), never from this file. */
(function () {
  "use strict";

  var TZ = (window.SITE && window.SITE.tz) || "America/Chicago";
  function store(key, val) {
    try {
      if (val === undefined) return JSON.parse(localStorage.getItem(key) || "null");
      localStorage.setItem(key, JSON.stringify(val));
    } catch (e) { return null; }
  }
  function fill(tpl, n) { return String(tpl || "").replace("{n}", n); }
  // The recounts below run every minute: a text is written only when it changes, so a screen reader
  // reading the page is never disturbed by the same words written again.
  function setText(el, v) { if (el.textContent !== v) el.textContent = v; }

  /* ------------------------------------------------------------------
     Deadlines: <span data-deadline="2026-10-15" data-t-days="{n} days left"
       data-t-today="…" data-t-tomorrow="…" data-t-past="…">
     The site is rebuilt daily, but a visitor may open a cached page — so the
     "days left" text is recomputed in the visitor's browser (Chicago dates). */
  function todayChicago() {
    try {
      var ymd = new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
      return new Date(ymd + "T12:00:00Z").getTime();
    } catch (e) { var d = new Date(); return Date.UTC(d.getFullYear(), d.getMonth(), d.getDate(), 12); }
  }
  function updateDeadlines() {
    var today = todayChicago();
    document.querySelectorAll("[data-deadline]").forEach(function (el) {
      var ymd = el.getAttribute("data-deadline");
      if (!/^\d{4}-\d{2}-\d{2}$/.test(ymd)) return;
      var days = Math.round((new Date(ymd + "T12:00:00Z").getTime() - today) / 864e5);
      var numEl = el.querySelector("[data-days-num]");
      if (numEl) setText(numEl, String(Math.max(0, days)));
      var unitEl = el.querySelector("[data-days-unit]");
      if (unitEl) setText(unitEl, el.getAttribute(days === 1 ? "data-t-unit1" : "data-t-unitn") || unitEl.textContent);
      var txt = days < 0 ? el.getAttribute("data-t-past") : days === 0 ? el.getAttribute("data-t-today")
        : days === 1 ? el.getAttribute("data-t-tomorrow") : fill(el.getAttribute("data-t-days"), days);
      var label = el.querySelector("[data-days-label]") || el;
      if (txt) setText(label, txt);
      var row = el.closest("[data-deadline-row]");
      if (row) row.classList.toggle("is-past", days < 0);
    });
  }

  /* ------------------------------------------------------------------
     "See who from our Area got published" card (/read/ and /contribute/): the numbers are
     counted when the site is built, so recount the "last N days" window here with the
     visitor's date (Central time) — the same rule as the home page (home.js spotlight) and
     /published/: story day >= today − N days. Each number carries one date per writer
     (data-dates: that writer's newest story) and each name chip its writer's date (data-date).
     Writers can only leave the window, so this only ever hides or lowers what the server drew:
     no Area 65 writer left → the "none from our Area" text and the Texas list; no Texas writer
     left → the plain text and no numbers. */
  function ymdToday() {
    try {
      var s = new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
      if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
    } catch (e) { /* fall through */ }
    return new Date().toISOString().slice(0, 10);
  }
  function ymdMinus(ymd, days) {
    var p = ymd.split("-");
    return new Date(Date.UTC(+p[0], +p[1] - 1, +p[2] - days)).toISOString().slice(0, 10);
  }
  function recountSpot(root) {
    var days = parseInt(root.getAttribute("data-spot-days"), 10);
    if (!(days > 0)) return;
    var cutoff = ymdMinus(ymdToday(), days);
    var n = { area: 0, texas: 0 };
    root.querySelectorAll("[data-spot-n]").forEach(function (dd) {
      var key = dd.getAttribute("data-spot-n"), c = 0;
      (dd.getAttribute("data-dates") || "").split(" ").forEach(function (d) { if (d && d >= cutoff) c++; });
      n[key] = c;
      setText(dd, String(c));
      var box = dd.parentNode, dt = box.querySelector("dt");
      if (dt) setText(dt, dt.getAttribute(c === 1 ? "data-one" : "data-many") || dt.textContent);
      box.hidden = !c;
    });
    root.querySelectorAll("[data-spot-list] [data-date]").forEach(function (li) {
      li.hidden = li.getAttribute("data-date") < cutoff;
    });
    var list = n.area ? "area" : "texas";
    root.querySelectorAll("[data-spot-list]").forEach(function (el) {
      el.hidden = el.getAttribute("data-spot-list") !== list || !el.querySelector("[data-date]:not([hidden])");
    });
    var nums = root.querySelector("[data-spot-nums]");
    if (nums) nums.hidden = !n.texas;
    var mode = !n.texas ? "nodata" : !n.area ? "none_area" : "main";
    root.querySelectorAll("[data-spot-text]").forEach(function (el) { el.hidden = el.getAttribute("data-spot-text") !== mode; });
  }
  function recountSpots() {
    document.querySelectorAll("[data-spot-days]").forEach(function (root) {
      try { recountSpot(root); } catch (e) { /* keep the server-rendered card */ }
    });
  }

  /* ------------------------------------------------------------------
     Share your story › "Next workshops" ([data-ws-list]): each row carries the moment its workshop
     ends ([data-cm-expire="ISO"], the same attribute as /events/ — committee.js is not loaded here).
     The page is built once a day, so a workshop that has ended hides itself, and the list with it
     when none is left — but never under the reader: a row that holds keyboard focus (its link) waits
     until focus leaves it, then goes (app.js GV.expire's rule). */
  function expireWorkshops() {
    var now = Date.now(), active = document.activeElement;
    document.querySelectorAll("[data-ws-list]").forEach(function (list) {
      var left = 0;
      list.querySelectorAll("[data-cm-expire]").forEach(function (el) {
        var t = Date.parse(el.getAttribute("data-cm-expire"));
        if (!(t && t <= now)) { left++; return; }
        if (!el.hidden && active && active !== document.body && el.contains(active)) {
          left++;
          if (!el.__wsExpireWait) {                  // try again once focus has moved on
            el.__wsExpireWait = true;
            el.addEventListener("focusout", function () {
              el.__wsExpireWait = false;
              setTimeout(expireWorkshops, 0);
            }, { once: true });
          }
          return;
        }
        el.hidden = true;
      });
      list.hidden = !left;
    });
  }

  /* ------------------------------------------------------------------
     "Did you know? / ¿Sabías que…?" (About, /gvr/: macros/question.njk): the build writes the next days'
     questions (eleventy/filters/booth.js dailyQuestions: { from, days: [[id …] …], items }); today's are the
     list of today's Central day — counted from `from`, so a page built days ago still changes every day. Past
     its last day (a page kept for offline use for longer) it goes round its days again — a day's list was made
     for an earlier day then, so dailyList leaves out each question outside its own from / until dates (a row about
     an event that is over) on the visitor's day; a clock set before `from` gets the first day. → the index of the
     day to show (0 with no days). */
  function dayIndex(from, today, n) {
    var re = /^\d{4}-\d{2}-\d{2}$/;
    if (!(n > 0) || !re.test(from || "") || !re.test(today || "")) return 0;
    var utc = function (s) { var p = s.split("-"); return Date.UTC(+p[0], +p[1] - 1, +p[2]); };
    var d = Math.round((utc(today) - utc(from)) / 864e5);
    return d < 0 ? 0 : d % n;
  }
  function dailyList(data, today) {
    if (!data || !Array.isArray(data.days) || !data.days.length || !data.items) return [];
    var ids = data.days[dayIndex(data.from, today, data.days.length)] || [];
    var day = /^\d{4}-\d{2}-\d{2}$/.test(today || "") ? today : "";
    return ids.map(function (id) { return data.items[id]; }).filter(function (it) {
      return !!it && typeof it.text === "string" && it.text !== "" &&
        !(day && typeof it.from === "string" && it.from > day) && !(day && typeof it.until === "string" && it.until < day);
    });
  }

  document.addEventListener("alpine:init", function () {
    var Alpine = window.Alpine;

    /* ---------------- Read page: publication filter + older issues ---------------- */
    Alpine.data("readPage", function (cfg) {
      cfg = cfg || {};
      return {
        pub: "all",
        older: [],
        loading: false,
        failed: false,
        remaining: Number(cfg.remaining) || 0,
        init: function () {
          var self = this;
          var saved = store("read-pub");
          // Remember the visitor's publication filter — only while the filter chips are on the page.
          if (cfg.chips && (saved === "gv" || saved === "lv")) this.pub = saved;
          // Arriving via "#gv-current" / "#lv-current": never hide the issue the visitor asked for.
          var h = (location.hash || "").replace("#", "");
          if (/^(gv|lv)-current$/.test(h) && !this.show(h.slice(0, 2))) this.pub = "all";
          // The same on the page: the hero's "This month's Grapevine" / "Current La Viña" buttons sit
          // outside this component, so a document-level listener catches them (and any other link to
          // #gv-current / #lv-current). When the saved filter hides that magazine, show both again,
          // then scroll to it once Alpine has shown it (x-show reveals on the next frame).
          document.addEventListener("click", function (e) {
            if (e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
            var a = e.target && e.target.closest ? e.target.closest('a[href^="#"]') : null;
            var id = a ? a.getAttribute("href").slice(1) : "";
            if (!/^(gv|lv)-current$/.test(id) || self.show(id.slice(0, 2))) return;   // visible: the normal jump works
            e.preventDefault();
            if (location.hash !== "#" + id) { try { history.pushState(null, "", "#" + id); } catch (err) { /* file:// etc. */ } }
            self.reveal(id);
          });
          window.addEventListener("hashchange", function () {
            var id = (location.hash || "").replace("#", "");
            if (/^(gv|lv)-current$/.test(id) && !self.show(id.slice(0, 2))) self.reveal(id);
          });
        },
        reveal: function (id) {
          this.pub = "all";
          var tries = 0;
          (function go() {
            var el = document.getElementById(id);
            if (!el) return;
            if (!el.getClientRects().length && tries++ < 20) { requestAnimationFrame(go); return; }
            el.scrollIntoView({ block: "start" });
          })();
        },
        show: function (p) { return this.pub === "all" || this.pub === p; },
        setPub: function (p) { this.pub = p; store("read-pub", p); },
        // Site-relative asset path ("/assets/cache/…") → URL that respects the site's base path.
        assetUrl: function (p) { return p && window.GV && window.GV.url ? window.GV.url(p) : p; },
        visibleCount: function () {
          var self = this, n = 0;
          (cfg.counts || []).forEach(function (c) { if (self.show(c)) n++; });
          this.older.forEach(function (i) { if (self.show(i.pub)) n++; });
          return n;
        },
        loadOlder: function () {
          var self = this;
          if (self.loading || !cfg.json) return;   // a second tap while loading just waits for the same fetch
          self.loading = true; self.failed = false;
          fetch(window.GV ? window.GV.url(cfg.json) : cfg.json, { cache: "no-cache" })
            .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
            .then(function (data) {
              self.older = (data && data.issues) || [];
              self.remaining = 0;
            })
            .catch(function () { self.failed = true; })
            .then(function () { self.loading = false; });
        },
      };
    });

    /* ---------------- GVR / RLV first-steps checklist (saved in this browser) ---------------- */
    Alpine.data("gvrChecklist", function (key, total) {
      return {
        key: key || "gvr-checklist-v1",
        total: Number(total) || 0,
        done: {},
        init: function () { this.done = store(this.key) || {}; },
        toggle: function (id) {
          var d = Object.assign({}, this.done);
          if (d[id]) delete d[id]; else d[id] = true;
          this.done = d;
          store(this.key, d);
        },
        isDone: function (id) { return !!this.done[id]; },
        count: function () { return Object.keys(this.done).length; },
        pct: function () { return this.total ? Math.round((this.count() / this.total) * 100) : 0; },
        reset: function () { this.done = {}; store(this.key, {}); },
      };
    });

    /* ---------------- "Did you know?": the booth's question of the day (dayIndex above) ----------------
       Tap an answer (a true or false, or one of a question's choices) or "Show the answer" (a sentence to
       complete): the answer, its explanation and source appear and the keyboard goes to them, so a screen reader
       reads them; "Another question" (the day's next one, up to its last) brings the keyboard back to the new
       question. The answers stay on screen once given (aria-disabled), marked with an icon and words. Nothing is
       stored: no score, no streak. The words come from the card (data-t-*). */
    Alpine.data("dailyQuestion", function () {
      var root = null;   // the card (kept out of Alpine's reactive data: a DOM element)
      // the card's question / answer box (inside the <template x-if>: $refs do not reach them), focused once it is
      // on screen — x-show shows an element on the next animation frame, after $nextTick (readPage.reveal's wait)
      function focusOn(sel, tries) {
        var el = root && root.querySelector(sel);
        if (!el) return;
        if (!el.getClientRects().length && (tries || 0) < 20) {
          requestAnimationFrame(function () { focusOn(sel, (tries || 0) + 1); });
          return;
        }
        el.focus();
      }
      return {
        list: [],
        i: 0,
        picked: null,
        shown: false,
        t: {},
        init: function () {
          var el = (root = this.$el), src = el.querySelector("script[data-dyk]"), data = null;
          try { data = JSON.parse(src ? src.textContent : "null"); } catch (e) { data = null; }
          this.list = dailyList(data, ymdToday());
          var t = {};
          ["true", "false", "gv", "lv", "both", "source"].forEach(function (k) { t[k] = el.getAttribute("data-t-" + k) || ""; });
          this.t = t;
        },
        cur: function () { return this.list[this.i] || null; },
        // a true or false: True, then False; a question: its choices; a sentence to complete: none
        options: function () {
          var it = this.cur();
          if (!it) return [];
          if (it.type === "truefalse") return [this.t["true"], this.t["false"]];
          return it.type === "quiz" && Array.isArray(it.choices) ? it.choices : [];
        },
        isRight: function (k) {
          var it = this.cur();
          if (!it || k === null || k === undefined) return false;
          return it.type === "truefalse" ? (k === 0) === (it.correct === true) : k === it.correct;
        },
        pubName: function () { var it = this.cur(); return it ? this.t[it.pub] || this.t.both : ""; },
        pubClass: function () { var it = this.cur(); return it && it.pub === "lv" ? "badge-lv" : it && it.pub === "gv" ? "badge-gv" : "badge-vine"; },
        answer: function (k) {
          if (this.shown) return;
          this.picked = k;
          this.reveal();
        },
        reveal: function () {
          this.shown = true;
          this.$nextTick(function () { focusOn(".read-dyk-fb", 0); });
        },
        more: function () { return this.shown && this.i < this.list.length - 1; },
        another: function () {
          if (!this.more()) return;
          this.i++;
          this.picked = null;
          this.shown = false;
          this.$nextTick(function () { focusOn(".read-dyk-q", 0); });
        },
      };
    });

    /* ---------------- GVR / RLV corner › "Pass it on" (#pass-it-on) ----------------
       The announcement and the welcome message are shown as they are copied (x-ref="announce" / "welcome": their
       lines as written — the welcome's meeting date is rolled on by app.js GV.meetingLines, so a copy says the next
       one); Copy (GV.copy: "Copied!" on the button and for a screen reader), Share (the device's own share sheet,
       only where there is one) and Print: one of the page's print-only sheets ("announce": the half-sheet,
       "handover") — html[data-print="gvr-…"] while the print dialog is open (read.css), as the share kit does. */
    Alpine.data("gvrPass", function () {
      return {
        canShare: !!(navigator && navigator.share),
        init: function () {
          window.addEventListener("afterprint", function () {
            var r = document.documentElement;
            if (/^gvr-/.test(r.getAttribute("data-print") || "")) r.removeAttribute("data-print");
          });
        },
        // the text as it is copied: each line trimmed, at most one empty line in a row
        text: function (ref) {
          var el = this.$refs[ref];
          if (!el) return "";
          return String(el.textContent || "").split("\n").map(function (l) { return l.replace(/\s+/g, " ").trim(); })
            .join("\n").replace(/\n{3,}/g, "\n\n").trim();
        },
        copy: function (ref, btn) { if (window.GV) window.GV.copy(this.text(ref), btn); },
        share: function (ref, btn) { if (window.GV) window.GV.share({ text: this.text(ref) }, btn); },
        print: function (which) {
          document.documentElement.setAttribute("data-print", "gvr-" + which);
          // Let the attribute apply before the print dialog takes its picture of the page.
          setTimeout(function () { window.print(); }, 60);
        },
      };
    });
  });

  /* ------------------------------------------------------------------
     "Add to my calendar" beside each story deadline (/contribute/: contribute.njk dlCalMenu, a <details
     class="cm-menu ct-dl-cal">): its .ics button downloads the deadline as /deadlines.ics has it (app.js GV.ics — the
     same UID and words, the reminder at 9 AM the day before). Bound on each button, not through the document:
     Chromium drops a download started from a document-level click (committee.js bindIcsButtons). One menu open at a
     time; a click elsewhere, a link chosen or Escape closes it (Escape: focus back on its button) — as committee.js
     does on its pages. A deadline that passes while the page is open loses its menu (read.css: .is-past). */
  function bindDeadlineCals() {
    document.querySelectorAll("[data-dl-ics]").forEach(function (b) {
      if (b._dlBound) return;
      b._dlBound = true;
      b.addEventListener("click", function (e) {
        e.preventDefault();
        try { if (window.GV && window.GV.ics) window.GV.ics(JSON.parse(b.getAttribute("data-dl-ics"))); } catch (err) { /* malformed data */ }
        var d = b.closest("details");
        if (d) d.removeAttribute("open");
      });
    });
  }
  function closeDlMenus(except) {
    document.querySelectorAll("details.ct-dl-cal[open]").forEach(function (d) { if (d !== except) d.removeAttribute("open"); });
  }
  document.addEventListener("click", function (e) {
    var menu = e.target && e.target.closest ? e.target.closest("details.ct-dl-cal") : null;
    closeDlMenus(menu);
    if (menu && e.target.closest(".cm-menu-panel a")) setTimeout(function () { menu.removeAttribute("open"); }, 0);
  });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    var open = document.querySelector("details.ct-dl-cal[open]");
    if (open) { open.removeAttribute("open"); var s = open.querySelector("summary"); if (s) s.focus(); }
  });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bindDeadlineCals);
  else bindDeadlineCals();

  function refresh() { updateDeadlines(); recountSpots(); expireWorkshops(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", refresh);
  else refresh();
  // A page left open: every minute (a workshop that has just ended goes, as on /events/ and the home page;
  // past midnight the days left and the writers' window move on), and when the page is shown again (a tab
  // brought back to the front, or a page restored by the Back button).
  setInterval(refresh, 60000);
  document.addEventListener("visibilitychange", function () { if (document.visibilityState === "visible") refresh(); });
  window.addEventListener("pageshow", function (e) { if (e.persisted) refresh(); });
})();
