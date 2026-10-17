/* Home page behaviour — NETA 65 Grapevine / La Viña.
   Loaded (defer) after app.js and before Alpine, so components register on alpine:init.

   - homeMeeting: live countdown to the next committee meeting (the card in the hero from
     1024px and the one under the hero on smaller screens — one of them is displayed). If the
     last site build is older than the meeting (e.g. the daily build failed for a few days),
     it works out the next date itself from the meeting rule, so the card is never out of date.
   - homePlayer: the "More episodes" play buttons load into the featured audio player, which keeps the same
     saved places as Listen's player (media.js — this device only): an episode goes on where it stopped, a
     finished one says "Played", and "Continue listening: <title> — 23 min left" offers the last one left
     part-way (wherever it was started).
   - Published-writers spotlight: recounts the "last 60 days" window with the visitor's own
     date (plain JS, no Alpine needed), so stories drop out on time between daily builds,
     and re-sizes the "see the full list" tile that closes the grid's last row.
   - Daily quote: "Today" / "Yesterday" next to each quote (Central time), the link name for a quote
     that is not today's ("Today's quote on …"), and on phones the button that shows the other
     magazine's quote.
   The hero art (hero-canvas.js, loaded by base.njk) sizes itself; nothing to do here. */
(function () {
  "use strict";
  var TZ = (window.SITE && window.SITE.tz) || "America/Chicago";

  function locale() {
    var lang = (window.GV && window.GV.lang) || document.documentElement.lang || "en";
    return lang === "es" ? "es-US" : "en-US";
  }

  // Same wording as the server-side filters (homeMeetingDate + homeTimeRange): the time with the site's own
  // helper (GVTime.timeRange, the build's clockRange), so a meeting that ends after midnight reads
  // "10:00 PM – 1:00 AM CDT", never Intl's "10/21/2026, 10:00 PM CDT – 10/22/2026, 1:00 AM CDT".
  function meetingLabels(start, end) {
    var loc = locale(), out = { date: "", time: "" }, T = window.GVTime;
    try {
      out.date = new Intl.DateTimeFormat(loc, { weekday: "long", month: "long", day: "numeric", timeZone: TZ }).format(start);
      if (loc === "es-US") out.date = out.date.charAt(0).toUpperCase() + out.date.slice(1);
      var tf = new Intl.DateTimeFormat(loc, { hour: "numeric", minute: "2-digit", timeZone: TZ, timeZoneName: "short" });
      if (T && T.timeRange) out.time = T.timeRange(start, end && end > start ? end : start, loc, TZ);
      else out.time = end && end > start && tf.formatRange ? tf.formatRange(start, end) : tf.format(start);
      if (window.GV && GV.esMeridiem) out.time = GV.esMeridiem(out.time); // "p. m." like the rest of the site (no-op in English)
    } catch (e) { /* very old browser: keep the server text */ }
    return out;
  }

  // "2026-10-21" — the meeting's calendar date in Central time (a 7 PM meeting is
  // already the next day in UTC, which made the file name look a day off).
  function localYmd(ms) {
    try {
      var p = new Intl.DateTimeFormat("en-CA", { year: "numeric", month: "2-digit", day: "2-digit", timeZone: TZ }).formatToParts(new Date(ms));
      var get = function (t) { for (var i = 0; i < p.length; i++) if (p[i].type === t) return p[i].value; return ""; };
      var s = get("year") + "-" + get("month") + "-" + get("day");
      if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
    } catch (e) { /* fall through */ }
    return new Date(ms).toISOString().slice(0, 10);
  }

  /* ---------- the episode player's saved places: Listen's own (src/assets/js/media.js) — keep the two in step ----------
     gv:audio:pos   { episodeId: [seconds (-1 = finished), savedAt] }, at most 150 (the oldest go)
     gv:audio:last  the last episode played: { id, t, a, art, du, sh, u, at } (for "Continue listening")
     Same keys and rules as media.js persist() / lastResume(): finished = within 20 s of the end; a place is kept
     from 5 s in; "Continue listening" = the last episode, more than 30 s in, played in the last 60 days. */
  var K_POS = "gv:audio:pos", K_LAST = "gv:audio:last", MAX_POS = 150;
  function lsJson(k) { try { return JSON.parse(window.localStorage.getItem(k)); } catch (e) { return null; } }
  function lsSet(k, v) { try { window.localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode / quota */ } }
  function positions() { var o = lsJson(K_POS); return o && typeof o === "object" && !Array.isArray(o) ? o : {}; }
  function savePosition(id, val) {
    var map = positions(), ids;
    map[id] = [val, Date.now()];
    ids = Object.keys(map);
    if (ids.length > MAX_POS) {
      ids.sort(function (a, b) { return ((map[b] && map[b][1]) || 0) - ((map[a] && map[a][1]) || 0); });
      ids.slice(MAX_POS).forEach(function (x) { delete map[x]; });
    }
    lsSet(K_POS, map);
  }
  function safeUrl(u) { u = String(u || ""); return /^(https?:\/\/|\/(?!\/))/i.test(u) ? u : ""; }
  function lastResume() {
    var last = lsJson(K_LAST);
    if (!last || typeof last !== "object" || !last.id || !safeUrl(last.a)) return null;
    var p = positions()[last.id];
    if (!Array.isArray(p) || !(p[0] > 30)) return null;
    if (last.at && Date.now() - last.at > 60 * 864e5) return null;
    return { id: String(last.id), t: String(last.t || ""), a: safeUrl(last.a), art: safeUrl(last.art), du: Number(last.du) || 0,
             sh: String(last.sh || ""), u: safeUrl(last.u), pos: p[0] };
  }
  /* 1938 → "32 min", 4000 → "1 h 07 min" (media.js mins); 1938 → "32:18" (media.js clock) */
  function pad(n) { return n < 10 ? "0" + n : String(n); }
  function mins(sec) {
    sec = Math.round(Number(sec) || 0);
    if (sec <= 0) return "";
    var m = Math.max(1, Math.round(sec / 60));
    return m < 60 ? m + " min" : Math.floor(m / 60) + " h " + pad(m % 60) + " min";
  }
  function clock(sec) {
    sec = Math.max(0, Math.floor(Number(sec) || 0));
    var h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
    return h ? h + ":" + pad(m) + ":" + pad(s) : m + ":" + pad(s);
  }
  /* An episode as the player saves it, from an element's data-* (the <audio> = the featured one; a "More
     episodes" play button = its own) */
  function epOf(ds) {
    return { id: ds.id || "", t: ds.title || "", a: safeUrl(ds.src), art: safeUrl(ds.img), du: Number(ds.du) || 0, sh: ds.sh || "", u: safeUrl(ds.u) };
  }

  document.addEventListener("alpine:init", function () {
    var Alpine = window.Alpine;

    Alpine.data("homeMeeting", function () {
      return {
        start: 0, end: 0, d: 0, h: 0, m: 0, s: 0,
        live: false, ready: false, rule: null, dateLabel: "", timeLabel: "",

        init: function () {
          var ds = this.$el.dataset;
          try { this.rule = JSON.parse(ds.rule || "null"); } catch (e) { this.rule = null; }
          this.start = Date.parse(ds.start) || 0;
          this.end = Date.parse(ds.end) || (this.start ? this.start + 3600e3 : 0);
          // Start from the server-rendered text so nothing flickers.
          this.dateLabel = this.$refs.date ? this.$refs.date.textContent.trim() : "";
          this.timeLabel = this.$refs.time ? this.$refs.time.textContent.trim() : "";
          this.tick();
          var self = this;
          this._timer = setInterval(function () { self.tick(); }, 1000);
          this.ready = true;
        },
        destroy: function () { clearInterval(this._timer); },

        // Move on to the next meeting once this one has ended.
        advance: function () {
          if (!this.rule || !window.GV || !window.GV.nextMeeting) return;
          var n = window.GV.nextMeeting(this.rule);
          if (!n || n.end.getTime() <= Date.now()) return;
          this.start = n.start.getTime();
          this.end = n.end.getTime();
          var l = meetingLabels(n.start, n.end);
          if (l.date) this.dateLabel = l.date;
          if (l.time) this.timeLabel = l.time;
        },

        tick: function () {
          var now = Date.now();
          if (this.end && now >= this.end) this.advance();
          this.live = !!this.start && now >= this.start && now < this.end;
          var diff = Math.max(0, this.start - now);
          this.d = Math.floor(diff / 864e5);
          this.h = Math.floor((diff % 864e5) / 36e5);
          this.m = Math.floor((diff % 36e5) / 6e4);
          this.s = Math.floor((diff % 6e4) / 1e3);
        },

        pad: function (n) { return n < 10 ? "0" + n : String(n); },

        addToCalendar: function () {
          if (!window.GV || !window.GV.ics || !this.start) return;
          var ds = this.$root.dataset; // $el would be the clicked button here
          window.GV.ics({
            title: ds.calTitle, description: ds.calDesc, location: ds.calLoc, url: ds.calLoc,
            start: new Date(this.start), end: new Date(this.end),
            // Same UID as the Events page / calendar feed use for this meeting, so adding it
            // twice updates the entry instead of duplicating it.
            uid: "ev-committee-" + localYmd(this.start) + (locale() === "es-US" ? "-es" : "") + "@neta65-gvlv",
            filename: "neta65-grapevine-committee-" + localYmd(this.start),
          });
        },
      };
    });

    Alpine.data("homePlayer", function () {
      return {
        current: "", playing: false, title: "", meta: "",
        ep: null, // what the player holds, as it is saved ({ id, t, a, art, du, sh, u } — epOf)
        started: false, // played since the page opened (only then is a place saved)
        want: 0, // where the next file starts, once its length is known (its saved place)
        saved: {}, // id → seconds (-1 = finished): this device's places, Listen's too
        resume: null, // "Continue listening" (lastResume), until something plays here
        lastSave: 0,

        init: function () {
          this.title = this.$refs.title ? this.$refs.title.textContent.trim() : "";
          this.meta = this.$refs.meta ? this.$refs.meta.textContent.trim() : "";
          var map = positions(), sv = {};
          for (var id in map) if (Array.isArray(map[id])) sv[id] = map[id][0];
          this.saved = sv;
          this.resume = lastResume();
          var a = this.$refs.audio, self = this;
          if (!a) return;
          this.ep = epOf(a.dataset);
          this.want = this.resumeAt(this.ep.id);
          a.addEventListener("play", function () { var had = self.inResume(); self.playing = true; self.started = true; if (had) self.focusPlayer(); });
          a.addEventListener("pause", function () { self.playing = false; self.persist(); });
          a.addEventListener("ended", function () { self.playing = false; self.persist(isFinite(a.duration) ? a.duration : null); });
          // the saved place, once the file's length is known (preload="none": on the first play)
          a.addEventListener("loadedmetadata", function () {
            var at = self.want, d = isFinite(a.duration) && a.duration > 0 ? a.duration : Infinity;
            self.want = 0;
            if (at > 0) { try { a.currentTime = Math.min(at, d - 1); } catch (e) { /* not seekable yet */ } }
          });
          a.addEventListener("timeupdate", function () { if (Date.now() - self.lastSave > 5000) { self.lastSave = Date.now(); self.persist(); } });
          window.addEventListener("pagehide", function () { self.persist(); });
          document.addEventListener("visibilitychange", function () { if (document.hidden) self.persist(); });
        },

        /* Save the place in what is playing (and "last played"), as Listen does. t overrides currentTime. */
        persist: function (t) {
          var a = this.$refs.audio, ep = this.ep;
          if (!a || !ep || !ep.id || !ep.a || !this.started) return;
          var time = t != null ? Number(t) : a.currentTime || 0;
          var dur = (isFinite(a.duration) && a.duration > 0 ? a.duration : 0) || ep.du || 0;
          var val = null;
          if (dur && time > 0 && dur - time < 20) val = -1; // finished
          else if (time >= 5) val = Math.floor(time);
          if (val !== null) { savePosition(ep.id, val); this.saved[ep.id] = val; }
          lsSet(K_LAST, { id: ep.id, t: ep.t, a: ep.a, art: ep.art, du: ep.du, sh: ep.sh, u: ep.u, at: Date.now() });
        },

        /* Load an episode ({ id, t, a, art, du, sh, u }) into the player at its saved place and play it. */
        load: function (ep, meta, art) {
          var a = this.$refs.audio;
          this.persist();
          this.ep = ep;
          this.current = ep.id;
          this.title = ep.t || this.title;
          this.meta = meta || "";
          if (this.$refs.art && art) { this.$refs.art.style.visibility = ""; this.$refs.art.src = art; }
          this.want = this.resumeAt(ep.id);
          a.src = ep.a;
          a.play().catch(function () {});
        },

        // el = the play link of an episode in the list (href = mp3, works without JS too)
        play: function (el) {
          var a = this.$refs.audio;
          if (!a) { window.open(el.href, "_blank", "noopener"); return; }
          var id = el.dataset.id;
          if (this.current === id) { if (a.paused) a.play().catch(function () {}); else a.pause(); return; }
          this.load(epOf(el.dataset), el.dataset.meta, el.dataset.img);
        },

        /* "Continue listening": the last episode left part-way (on Home or on Listen) */
        resumeLast: function () {
          var r = this.resume;
          if (!r || !this.$refs.audio) return;
          var had = this.inResume();
          this.resume = null;
          if (had) this.focusPlayer();
          if (this.current === r.id) { this.$refs.audio.play().catch(function () {}); return; }
          this.load({ id: r.id, t: r.t, a: r.a, art: r.art, du: r.du, sh: r.sh, u: r.u }, "", r.art);
        },
        /* Keyboard focus is in the "Continue listening" box, which goes away (Resume pressed, or something plays) */
        inResume: function () {
          var box = this.$refs.resume;
          return !!box && box.contains(document.activeElement);
        },
        /* … so the keyboard goes on from the player's controls (the episode now in it), not from the page's start */
        focusPlayer: function () {
          var a = this.$refs.audio, t = this.$refs.title;
          this.$nextTick(function () {
            try { a.focus(); } catch (e) { /* not focusable here */ }
            if (document.activeElement !== a && t) { t.setAttribute("tabindex", "-1"); t.focus(); }
          });
        },
        /* "23 min left" (or "at 12:34" when the length is not known) — data-left: "{t} left" / "quedan {t}" (after a dash) */
        resumeLeft: function () {
          var r = this.resume;
          if (!r) return "";
          return r.du > r.pos ? String(this.$root.dataset.left || "{t}").replace("{t}", mins(r.du - r.pos)) : clock(r.pos);
        },
        resumeLabel: function () { return (this.$root.dataset.resume || "") + (this.resume ? ": " + this.resume.t : ""); },

        resumeAt: function (id) { var v = this.saved[id]; return v > 0 ? v : 0; },
        isLoaded: function (id) { return this.started && !!this.ep && this.ep.id === id; },
        isDone: function (id) { return this.saved[id] === -1 && !this.isLoaded(id); },
        isPlaying: function (id) { return this.current === id && this.playing; },
      };
    });
  });

  /* ---------- Published-writers spotlight: keep the "last N days" window current ----------
     The page is built once a day; this recounts with the visitor's date (Central time, like
     the build — eleventy/filters/home.js homeSpotlight: pub_date >= today − N days) and hides
     the stories that have left the window since, then updates the counts, the notes
     ("no Area 65 story" / "no Texas story") and the "see the full list" tile that closes the
     grid's last row (fillGrid). Stories can only leave the window, never join it, so it only
     ever hides what the server rendered. The column count per screen width is CSS
     (home.css), so nothing needs redoing on resize. */
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
  /* How the grid closes its last row at `cols` columns: `a` Area 65 cards two columns wide (or
     the two-column "no Area 65 story" note when a = 0 and t > 0), then `t` Texas cards, placed
     like CSS `grid-auto-flow: row dense`. → { span: empty columns at the end of the last row
     (the "see the full list" tile fills them; 0 = no tile), full: Area 65 cards would leave gaps
     higher up, so each takes a whole row }. Same function as spotFill in
     eleventy/filters/home.js (which renders the first version): keep the two in step. */
  function spotFill(a, t, cols) {
    function run(featSpan) {
      var rows = [];
      function put(span) {
        for (var r = 0; ; r++) {
          if (!rows[r]) { rows[r] = []; for (var z = 0; z < cols; z++) rows[r].push(false); }
          for (var c = 0; c + span <= cols; c++) {
            var ok = true;
            for (var k = c; k < c + span; k++) if (rows[r][k]) { ok = false; break; }
            if (ok) { for (k = c; k < c + span; k++) rows[r][k] = true; return; }
          }
        }
      }
      var i;
      if (a > 0) for (i = 0; i < a; i++) put(featSpan);
      else if (t > 0) put(Math.min(2, cols));
      for (i = 0; i < t; i++) put(1);
      var free = 0, trailing = 0, last = rows[rows.length - 1] || [];
      for (i = 0; i < rows.length; i++) for (var j = 0; j < cols; j++) if (!rows[i][j]) free++;
      for (var n = last.length - 1; n >= 0 && !last[n]; n--) trailing++;
      return { free: free, trailing: trailing };
    }
    if (!a && !t) return { span: 0, full: false };
    var res = run(Math.min(2, cols)), full = false;
    if (res.free !== res.trailing) { full = true; res = run(cols); }
    return { span: res.trailing, full: full };
  }
  // Write the tile spans (data-f2…data-f5) and the whole-row columns (data-full) that home.css reads.
  function fillGrid(root, a, t) {
    var grid = root.querySelector("[data-spot-grid]"), tile = root.querySelector("[data-spot-fill]");
    if (!grid || !tile) return;
    var full = [];
    for (var cols = 2; cols <= 5; cols++) {
      var r = spotFill(a, t, cols);
      tile.setAttribute("data-f" + cols, String(r.span));
      if (r.full) full.push(cols);
    }
    if (full.length) grid.setAttribute("data-full", full.join(" ")); else grid.removeAttribute("data-full");
  }

  function spotlight(root) {
    var days = parseInt(root.getAttribute("data-days"), 10);
    if (!(days > 0)) return;
    var cutoff = ymdMinus(ymdToday(), days);
    var counts = { neta65: 0, texas: 0 };
    var items = root.querySelectorAll("[data-pub]");
    for (var i = 0; i < items.length; i++) {
      var li = items[i], pub = li.getAttribute("data-pub") || "";
      if (/^\d{4}-\d{2}-\d{2}$/.test(pub) && pub < cutoff) li.hidden = true;
      if (!li.hidden) counts[li.getAttribute("data-scope")] = (counts[li.getAttribute("data-scope")] || 0) + 1;
    }
    var total = counts.neta65 + counts.texas;
    var lists = root.querySelectorAll("[data-spot-list]");
    for (var j = 0; j < lists.length; j++) lists[j].hidden = !lists[j].querySelector("[data-pub]:not([hidden])");
    var toggle = function (sel, hide) { var el = root.querySelector(sel); if (el) el.hidden = hide; };
    toggle("[data-spot-grid]", !total);
    toggle("[data-spot-empty]", !!total);
    toggle("[data-spot-counts]", !total);
    toggle("[data-spot-none-a65]", counts.neta65 > 0 || counts.texas === 0);
    fillGrid(root, counts.neta65, counts.texas);
    var nf = null;
    try { nf = new Intl.NumberFormat(locale()); } catch (e) { nf = null; }
    var chips = root.querySelectorAll("[data-spot-count]");
    for (var k = 0; k < chips.length; k++) {
      var chip = chips[k], n = counts[chip.getAttribute("data-spot-count")] || 0;
      chip.hidden = !n;
      var tpl = n === 1 ? chip.getAttribute("data-one") : chip.getAttribute("data-many");
      var txt = chip.querySelector("[data-text]");
      if (txt && tpl) txt.textContent = tpl.replace("{n}", nf ? nf.format(n) : String(n));
    }
  }
  function initSpotlights() {
    var roots = document.querySelectorAll("[data-home-spot]");
    for (var i = 0; i < roots.length; i++) {
      try { spotlight(roots[i]); } catch (e) { /* keep the server-rendered list */ }
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initSpotlights); else initSpotlights();

  /* Daily quote card: the "Today" / "Yesterday" badge of each quote (data-quote-day, Central time), and
     its first link: "Read it on …" for today's quote, "Today's quote on …" for an older one (the
     official page shows a newer quote by then). The server never says "today" (the page may be read
     the next morning, before the new quote is on the site); a tab left open overnight is re-checked
     when it comes back into view. */
  function markQuoteToday() {
    var today = ymdToday(), yesterday = ymdMinus(today, 1), quotes = document.querySelectorAll("[data-quote-day]");
    for (var i = 0; i < quotes.length; i++) {
      var day = quotes[i].getAttribute("data-quote-day"), isToday = day === today;
      var t = quotes[i].querySelector("[data-quote-today]"), y = quotes[i].querySelector("[data-quote-yesterday]");
      if (t) t.hidden = !isToday;
      if (y) y.hidden = day !== yesterday;
      var names = quotes[i].querySelectorAll("[data-quote-link]");
      for (var k = 0; k < names.length; k++) names[k].hidden = (names[k].getAttribute("data-quote-link") === "this") !== isToday;
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", markQuoteToday); else markQuoteToday();
  document.addEventListener("visibilitychange", function () { if (!document.hidden) markQuoteToday(); });

  /* Phones (< 640px): only the page language's quote shows; the button opens the other magazine's
     (home.css hides it while the card is not .is-open — only with JS, so nothing is ever unreachable). */
  function initQuoteToggle() {
    var btns = document.querySelectorAll("[data-quote-toggle]");
    for (var i = 0; i < btns.length; i++) {
      btns[i].addEventListener("click", function () {
        var open = this.getAttribute("aria-expanded") !== "true", grid = this.closest("[data-quote-grid]");
        this.setAttribute("aria-expanded", open ? "true" : "false");
        if (grid) grid.classList.toggle("is-open", open);
      });
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initQuoteToggle); else initQuoteToggle();
})();
