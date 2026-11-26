/* Committee pages (Meetings, Events, Documents, Photos, Bulletin).
   Loaded with `defer` after app.js and BEFORE Alpine, so the Alpine
   components below are registered in time (alpine:init).
   No build step, no dependencies besides window.GV (app.js), window.GVTime
   (central-time.js: the time-zone math, loaded before app.js), Alpine and —
   on /photos/ only — GLightbox (self-hosted, MIT). */
(function () {
  "use strict";
  var GV = window.GV || {};
  var T = window.GVTime || null;
  var LANG = GV.lang || document.documentElement.lang || "en";
  var LOCALE = LANG === "es" ? "es-US" : "en-US";
  var TZ = (window.SITE && window.SITE.tz) || "America/Chicago";
  // The OS setting or the site's own "Reduce motion" (app.js GV.reducedMotion, loaded first)
  var REDUCED = window.GV && window.GV.reducedMotion ? window.GV.reducedMotion() : (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  var CM = (window.CM = window.CM || {});

  document.documentElement.classList.add("cm-js");

  /* ---------------- formatting helpers ---------------- */
  // Spanish "7:00 p.m." → "7:00 p. m." (no-break spaces), the site's one spelling — the same as the
  // build's text, so a label redrawn here (the meeting's time line on /es/meetings/, the Weekly Open
  // date, "Your time: …") never changes style. GV.esMeridiem (app.js) is a no-op on English pages.
  var meridiem = typeof GV.esMeridiem === "function" ? GV.esMeridiem : function (s) {
    return LANG === "es" ? String(s).replace(/\b([ap])\.\s?m\./g, "$1.\u00a0m.").replace(/(\d) (?=[ap]\.\u00a0m\.)/g, "$1\u00a0") : s;
  };
  function fmt(d, opts, tz) {
    try { return meridiem(new Intl.DateTimeFormat(LOCALE, Object.assign({ timeZone: tz || TZ }, opts)).format(d)); } catch (e) { return ""; }
  }
  // A start and an end time with the zone: "7:00 – 8:00 PM CDT"; one that ends after midnight (the visitor's own
  // midnight, for "Your time") "7:00 PM – 1:00 AM CST", never Intl's numeric dates (GVTime.timeRange, the build's
  // clockRange). opts: more Intl options for each end ({ weekday: "short" }).
  function range(a, b, opts, tz) {
    if (T) return meridiem(T.timeRange(a, b, LOCALE, tz || TZ, opts));
    try {
      var f = new Intl.DateTimeFormat(LOCALE, Object.assign({ timeZone: tz || TZ, hour: "numeric", minute: "2-digit", timeZoneName: "short" }, opts));
      return meridiem(f.formatRange ? f.formatRange(a, b) : f.format(a) + " – " + f.format(b));
    } catch (e) { return ""; }
  }
  function cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }
  // text for an HTML attribute (the lightbox's labels)
  function escAttr(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function utcStamp(d) { return new Date(d).toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, ""); }
  function ymdCompact(s) { return String(s).slice(0, 10).replace(/-/g, ""); }
  function ymdAdd(s, n) {
    var p = String(s).slice(0, 10).split("-").map(Number);
    return new Date(Date.UTC(p[0], p[1] - 1, p[2] + n)).toISOString().slice(0, 10);
  }
  function chicagoYmd(d) {
    try { return new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(d); } catch (e) { return new Date(d).toISOString().slice(0, 10); }
  }
  // Live-region count: data-count-label="Showing {n} events" + data-count-label-one="Showing 1 event"
  function countLabels(root) {
    var many = root.getAttribute("data-count-label") || "{n}";
    return { many: many, one: root.getAttribute("data-count-label-one") || many };
  }
  function countText(labels, n) { return (n === 1 ? labels.one : labels.many).replace("{n}", n); }

  /* ---------------- calendar links + .ics download ---------------- */
  // ev: {title, description, location, url, start, end, allDay, uid, filename}
  CM.calLinks = function (ev) {
    var q = function (o) { return Object.keys(o).map(function (k) { return k + "=" + encodeURIComponent(o[k]); }).join("&"); };
    var gd, os, oe;
    if (ev.allDay) {
      gd = ymdCompact(ev.start) + "/" + ymdCompact(ymdAdd(ev.end || ev.start, 1));
      os = String(ev.start).slice(0, 10); oe = ymdAdd(ev.end || ev.start, 1);
    } else {
      gd = utcStamp(ev.start) + "/" + utcStamp(ev.end || ev.start);
      os = new Date(ev.start).toISOString().replace(/\.\d{3}/, ""); oe = new Date(ev.end || ev.start).toISOString().replace(/\.\d{3}/, "");
    }
    return {
      gcal: "https://calendar.google.com/calendar/render?" + q({ action: "TEMPLATE", text: ev.title || "", dates: gd, details: ev.description || "", location: ev.location || "", ctz: TZ }),
      outlook: "https://outlook.live.com/calendar/0/action/compose?" + q({ rru: "addevent", subject: ev.title || "", startdt: os, enddt: oe, allday: ev.allDay ? "true" : "false", body: ev.description || "", location: ev.location || "" }),
    };
  };

  // One event as a calendar file: the browser's one .ics writer, app.js GV.ics / GV.icsText (the UID kept, a
  // SEQUENCE that is higher in every newer file, STATUS:TENTATIVE for ev.tentative). ev.allDay: start / end are
  // "YYYY-MM-DD" and end is the LAST day; the file gets DATE values with the exclusive DTEND (the day after),
  // like /events.ics.
  CM.downloadIcs = function (ev) {
    if (GV.ics) GV.ics(ev);
  };

  /* ---------------- Alpine components ---------------- */
  document.addEventListener("alpine:init", function () {
    var Alpine = window.Alpine;

    /* Next meeting — the committee meeting (/meetings/, /events/) or one of our monthly series (the Grapevine
       Meeting, /meetings/#grapevine-meeting): live countdown, "soon" (5 minutes before: the room opens a few
       minutes before we start) and "live" (until the end), labels in Central time + the visitor's own time,
       calendar links. Once a meeting is over it rolls on to the next date — with THAT date's guest speaker
       (speaker, speakerLine: none on a date without one) and calendar text.
       x-data="cmMeeting({rule, start, end, title, description, location, url, i18n, speakers, plain, uid, file, first})"
         speakers  the guest speakers to come: [{ ymd, name, position, topic, description }] (eleventy/filters/
                   committee.js cmSpeakers: description = that meeting's calendar text); plain: the calendar text
                   of a date without one (none given: `description`, the build's next date's)
         uid, file the calendar UID and file name before the date — "ev-committee-" / "committee-meeting-" when
                   left out; a series' "ev-recurring-grapevine-meeting-": the UID /events.ics gives that date, so
                   adding it twice keeps one entry
         first     a series' first date ("2027-01-06"): isFirst on that date ("First meeting") */
    Alpine.data("cmMeeting", function (cfg) {
      cfg = cfg || {};
      var i18n = cfg.i18n || {};
      var speakers = Array.isArray(cfg.speakers) ? cfg.speakers : [];
      function speakerOn(ymd) {
        for (var i = 0; i < speakers.length; i++) if (speakers[i] && speakers[i].ymd === ymd && speakers[i].name) return speakers[i];
        return null;
      }
      return {
        phase: "upcoming", d: 0, h: 0, m: 0, s: 0,
        dateLabel: "", timeLabel: "", whenLabel: "", localLabel: "", joinText: i18n.join || "",
        tile: { mon: "", day: "", wd: "" }, gcal: "", outlook: "",
        speaker: null, speakerLine: "", isFirst: false,
        _start: null, _end: null, _ymd: "", _desc: cfg.description || "",
        init: function () {
          this.compute();
          this.tick();
          var self = this;
          this._t = setInterval(function () { self.tick(); }, 1000);
        },
        destroy: function () { clearInterval(this._t); },
        compute: function () {
          var nx = null;
          try { if (cfg.rule && GV.nextMeeting) nx = GV.nextMeeting(cfg.rule); } catch (e) { nx = null; }
          var start = nx ? nx.start : new Date(cfg.start), end = nx ? nx.end : new Date(cfg.end || cfg.start);
          if (isNaN(start)) return;
          this._start = start; this._end = end; this._ymd = nx ? nx.ymd : chicagoYmd(start);
          // that date's guest speaker and calendar text
          var sp = speakerOn(this._ymd);
          this.speaker = sp ? { name: String(sp.name), position: String(sp.position || ""), topic: String(sp.topic || "") } : null;
          this.speakerLine = sp ? String(i18n.speaker || "{name}").replace("{name}", sp.name) : "";
          this._desc = sp && sp.description ? sp.description : (cfg.plain != null ? cfg.plain : cfg.description || "");
          this.isFirst = !!cfg.first && this._ymd === cfg.first;
          this.dateLabel = cap(fmt(start, { weekday: "long", month: "long", day: "numeric", year: "numeric" }));
          this.timeLabel = range(start, end);
          // One line for the hero: "Wednesday, October 21 · 7:00 PM CDT" (same as the build's whenLabel)
          this.whenLabel = cap(fmt(start, { weekday: "long", month: "long", day: "numeric" })) + " · " + fmt(start, { hour: "numeric", minute: "2-digit", timeZoneName: "short" });
          this.tile = {
            mon: fmt(start, { month: "short" }).replace(/\.$/, ""),
            day: fmt(start, { day: "numeric" }),
            wd: fmt(start, { weekday: "short" }).replace(/\.$/, ""),
          };
          // Visitor in another time zone? Show "Your time: …" too.
          this.localLabel = "";
          try {
            var local = Intl.DateTimeFormat().resolvedOptions().timeZone;
            var probe = { hour: "numeric", minute: "numeric", day: "numeric" };
            if (local && fmt(start, probe, local) !== fmt(start, probe, TZ)) {
              var lr = range(start, end, { weekday: "short" }, local);
              this.localLabel = String(i18n.yourTime || "{time}").replace("{time}", lr);
            }
          } catch (e) {}
          var links = CM.calLinks({ title: cfg.title, description: this._desc, location: cfg.location, start: start, end: end });
          this.gcal = links.gcal; this.outlook = links.outlook;
        },
        tick: function () {
          if (!this._start) return;
          var now = Date.now();
          if (this._end && now >= this._end.getTime()) this.compute(); // meeting over → roll to the next one
          var st = this._start.getTime(), diff = st - now;
          // (live until its end: a meeting that could not be rolled on — no GVTime — is not "live" for ever; "soon"
          // the last 5 minutes: the room opens a few minutes before we start — the host opens it at 6:50 PM, and
          // the committee's Google Workspace account gives the call no time limit)
          this.phase = now >= st ? (this._end && now >= this._end.getTime() ? "upcoming" : "live") : diff <= 5 * 60000 ? "soon" : "upcoming";
          this.joinText = this.phase === "live" ? i18n.live : this.phase === "soon" ? i18n.soon : i18n.join;
          diff = Math.max(0, diff);
          this.d = Math.floor(diff / 864e5); this.h = Math.floor((diff % 864e5) / 36e5);
          this.m = Math.floor((diff % 36e5) / 6e4); this.s = Math.floor((diff % 6e4) / 1e3);
        },
        pad: function (n) { return String(n).padStart(2, "0"); },
        downloadIcs: function () {
          if (!this._start) return;
          CM.downloadIcs({
            uid: (cfg.uid || "ev-committee-") + this._ymd + (LANG !== "en" ? "-" + LANG : "") + "@neta65-gvlv",
            title: cfg.title, description: this._desc, location: cfg.location, url: cfg.url,
            start: this._start, end: this._end, allDay: false, filename: (cfg.file || "committee-meeting-") + this._ymd,
          });
          closeMenus();
        },
      };
    });

    /* /events/: the filters, the months folded behind "Show 2028 dates (n)" and the way to any card. x-data="cmEvents()"
       on the agenda's <section>. Every card of the list is an li[data-group] (events.njk): a one-off event (a cancelled
       one too: data-ev-cancelled), a monthly series' card (#ev-pinned) and a weekly open meeting (#ev-weekly), each
       with its facets (eleventy/filters/event-list.js evFacets): data-kind (one word), data-lang (en · es · both),
       data-mode ("inperson", "online", or both words), data-city (a slug), data-district (a number).
       The filters (f): the kind (a chip: setKind), the language, in person / online, the city and the district (the
       menus: x-model, changed()) — a card shows when it matches every one picked ("" = any: picked). Each kind chip
       counts the cards it would show with the other filters as they are (kindCount); "Clear filters" (clear) sets
       them all back. The filters picked are kept in the address (?kind=workshop&lang=es&mode=inperson&city=…&
       district=…, history.replaceState: no new history entry), so a filtered view can be shared and comes back on
       reload; a value the page has no card for is left out. The page's old chips are still understood:
       ?filter=committee (the committee meetings) and ?filter=calendar (the GV & LV calendars) set the kind;
       ?filter=neta (its "NETA 65 events": ours and the committee meetings, data-group~="neta") is a filter of its own
       (`group`: no menu, a pressed chip of its own while it is on — a click, or "Clear filters", lets it go), kept in
       the address as it came (?filter=neta), the other filters beside it.
       The months: those of the years after the build's — after the next one from November on (eventsFold,
       eleventy/filters/committee.js) — are folded — the month section and its jump chip carry data-cm-more —, shown
       once `more` is true: "Show 2028 dates (n)" (showMore; n = the folded cards the filters would show: moreCount)
       moves the keyboard to the first month it shows (its heading, tabindex="-1"), and the button goes. A link to a
       folded card, or to its month, opens them too. Without JavaScript every month and every card shows, and the
       filters and the button are hidden ([data-js-only]).
       A link to a card — on load, on every hashchange, from the "Next 5 weeks" calendar's day panel, which
       dispatches window "cm:reveal" { detail: { id } } when its link points at the address's own #hash (no
       hashchange then), "Next up", and any other link to the address's own #hash (a click, e.g. "Save the date"
       again) — shows it (go): a card the filters hide clears them, a folded one opens the fold; a date of a series
       (its anchor on its series' card, hidden there — a date after the three the card lists) brings its card; then
       reveal() brings it into view, marks it a moment (.cm-flash) and gives it the keyboard focus (tabindex="-1",
       without scrolling again). A card whose time has passed (expire(): data-cm-expired) is left alone — it is gone.
       On load a link to a past event opens the "Past events" list (as before).
       "Showing N events" counts the cards that show, never a cancelled one. An event whose time passes while the page
       is open is hidden by expire() (below), which then says so ("cm:expired"): `tick` moves on, so every list,
       month heading and month chip (show / monthVisible), the counts and the "Show more" count are worked out
       again — they read only Alpine's own state, which no hidden card changes. */
    Alpine.data("cmEvents", function () {
      var FACETS = ["kind", "lang", "mode", "city", "district"];
      // ?filter= (the page's old chips) → [the filter it sets, its value]
      var LEGACY = { committee: ["kind", "committee"], calendar: ["kind", "calendar"], neta: ["group", "neta"] };
      function hashId() {
        try { return location.hash ? decodeURIComponent(location.hash.slice(1)) : ""; } catch (e) { return ""; }
      }
      function words(el, k) { return String(el.getAttribute("data-" + k) || "").split(/\s+/).filter(Boolean); }
      function cards(root) { return root.querySelectorAll("li[data-group]"); }
      function live(li) { return !li.hasAttribute("data-cm-expired"); }
      return {
        f: { kind: "", lang: "", mode: "", city: "", district: "" }, group: "", moreOpen: false,
        more: false, labels: { many: "{n}", one: "{n}" }, tick: 0,
        init: function () {
          var self = this;
          this.labels = countLabels(this.$root);
          // an event over while the page is open (expire()): counted again; a kind with no card left lets go
          window.addEventListener("cm:expired", function () {
            self.tick++;
            var k = self.f.kind;
            if (k && !Array.prototype.some.call(cards(self.$root), function (li) { return live(li) && words(li, "kind").indexOf(k) !== -1; })) self.setKind(k);
          });
          // x-show now owns what is hidden: drop the first-paint rule (committee.css [data-dflt-hidden])
          this.$nextTick(function () { document.documentElement.classList.add("cm-ev-ready"); });
          this.fromAddress();
          // (phones: the menus fold behind "More filters" — open when the address picked one of them)
          this.moreOpen = !!(this.f.lang || this.f.mode || this.f.city || this.f.district);
          // A link to a card (a folded month's, one the filters hide …) → show it; to a past event → open the
          // "Past events" list.
          var id = hashId(), el = this.go(id), past = !el && id && document.getElementById(id);
          if (el) this.reveal(el);
          else if (past && past.closest && past.closest("details[data-cm-past]")) {
            past.closest("details[data-cm-past]").open = true;
            // (an old anchor — evOldAnchors — is an empty span on its row: the row is marked)
            var row = past.closest("li") || past;
            row.classList.add("cm-target");
            this.$nextTick(function () { row.scrollIntoView({ block: "start" }); });
          }
          window.addEventListener("hashchange", function () {
            var t = self.go(hashId());
            if (t) self.reveal(t);
          });
          // the "Next 5 weeks" calendar's link to the address's own #hash (the browser sends no hashchange)
          window.addEventListener("cm:reveal", function (e) {
            var t = self.go(e && e.detail ? String(e.detail.id || "") : "");
            if (t) self.reveal(t);
          });
          // any other link of the page to the address's own #hash — "Save the date" clicked a second time after a
          // filter hid its card — gets the same: no hashchange comes then either (the calendar says "cm:reveal" itself)
          document.addEventListener("click", function (e) {
            var a = e.target && e.target.closest ? e.target.closest('a[href^="#"]') : null;
            if (!a || a.closest("[data-cm-cal]")) return;
            var id = "";
            try { id = decodeURIComponent(a.getAttribute("href").slice(1)); } catch (err) { return; }
            if (!id || id !== hashId()) return;
            var t = self.go(id);
            if (t) self.reveal(t);
          });
        },
        /* the values the page offers for a filter: its chips' (data-ev-kind) or its menu's options */
        offered: function (k) {
          var root = this.$root;
          if (k === "kind") return Array.prototype.map.call(root.querySelectorAll("[data-ev-kind]"), function (b) { return b.getAttribute("data-ev-kind"); });
          var sel = root.querySelector('select[data-ev-facet="' + k + '"]');
          return sel ? Array.prototype.map.call(sel.querySelectorAll("option"), function (o) { return o.getAttribute("value") || ""; }) : [];
        },
        /* the filters from the address (?kind=…&lang=… — ?filter=committee / calendar / neta too), each only when the
           page offers it (?kind= before ?filter=) */
        fromAddress: function () {
          var q;
          try { q = new URLSearchParams(location.search); } catch (e) { return; }
          var old = LEGACY[q.get("filter") || ""] || ["", ""];
          for (var i = 0; i < FACETS.length; i++) {
            var k = FACETS[i], v = q.get(k) || (k === old[0] ? old[1] : "");
            if (v && this.offered(k).indexOf(v) !== -1) this.f[k] = v;
          }
          if (old[0] === "group" && Array.prototype.some.call(cards(this.$root), function (li) { return words(li, "group").indexOf(old[1]) !== -1; })) this.group = old[1];
        },
        /* the filters into the address: ?kind=…&lang=… (the other parameters and the #hash stay; the old ?filter= goes,
           but for ?filter=neta while `group` is on) */
        toAddress: function () {
          try {
            var u = new URL(location.href);
            if (this.group) u.searchParams.set("filter", this.group); else u.searchParams.delete("filter");
            for (var i = 0; i < FACETS.length; i++) {
              var k = FACETS[i];
              if (this.f[k]) u.searchParams.set(k, this.f[k]); else u.searchParams.delete(k);
            }
            if (u.href !== location.href) history.replaceState(history.state, "", u.pathname + u.search + u.hash);
          } catch (e) { /* an old browser: the filters still work, the address stays */ }
        },
        setKind: function (k) { this.f.kind = this.f.kind === k ? "" : k; this.toAddress(); },
        changed: function () { this.toAddress(); },
        dropGroup: function () { this.group = ""; this.toAddress(); },
        clear: function () {
          for (var i = 0; i < FACETS.length; i++) this.f[FACETS[i]] = "";
          this.group = "";
          this.toAddress();
        },
        get active() {
          if (this.group) return true;
          for (var i = 0; i < FACETS.length; i++) if (this.f[FACETS[i]]) return true;
          return false;
        },
        /* the filters picked show this card (whatever the fold) — `skip`: one filter left out (a chip's count) */
        picked: function (el, skip) {
          if (this.group && words(el, "group").indexOf(this.group) === -1) return false;
          for (var i = 0; i < FACETS.length; i++) {
            var k = FACETS[i], v = this.f[k];
            if (v && k !== skip && words(el, k).indexOf(v) === -1) return false;
          }
          return true;
        },
        show: function (el) {
          void this.tick; // (read: worked out again after expire())
          if (!live(el)) return false;
          // (`more` read first, so Alpine works it out again once the fold opens)
          if (!this.more && el.closest("[data-cm-more]")) return false;
          return this.picked(el);
        },
        monthVisible: function (el) {
          var self = this;
          return !!el && Array.prototype.some.call(el.querySelectorAll("li[data-group]"), function (li) { return self.show(li); });
        },
        /* the month chips' row shows while one of its chips does: a month (an open one, or a folded one once `more`),
           "Every month" or "Every week" with a card the filters show — else its icon would stand there alone */
        get anyMonth() {
          var self = this;
          return Array.prototype.some.call(this.$root.querySelectorAll("[data-cm-month], #ev-pinned, #ev-weekly"), function (m) {
            return (self.more || !m.hasAttribute("data-cm-more")) && self.monthVisible(m);
          });
        },
        /* a kind chip's count: the cards of that kind the other filters show (the folded months' too — a click away),
           never a cancelled one */
        kindCount: function (k) {
          void this.tick;
          var self = this;
          return Array.prototype.filter.call(cards(this.$root), function (li) {
            return live(li) && !li.hasAttribute("data-ev-cancelled") && words(li, "kind").indexOf(k) !== -1 && self.picked(li, "kind");
          }).length;
        },
        get visibleCount() {
          var self = this;
          return Array.prototype.filter.call(cards(this.$root), function (li) { return !li.hasAttribute("data-ev-cancelled") && self.show(li); }).length;
        },
        countText: function () { return countText(this.labels, this.visibleCount); },
        /* the folded cards the filters would show: "Show 2028 dates (n)"; 0 → the button hides */
        get moreCount() {
          void this.tick;
          var self = this, n = 0;
          this.$root.querySelectorAll("section[data-cm-more]").forEach(function (m) {
            Array.prototype.forEach.call(m.querySelectorAll("li[data-group]"), function (li) {
              if (live(li) && !li.hasAttribute("data-ev-cancelled") && self.picked(li)) n++;
            });
          });
          return n;
        },
        moreText: function (el) {
          return String(el.getAttribute("data-label") || "{n}").replace("{n}", this.moreCount);
        },
        /* "Show 2028 dates": the folded months show, and the keyboard goes on to the first of them that shows
           something for the filters picked (its heading) — the pressed button disappears */
        showMore: function () {
          var self = this;
          this.more = true;
          this.$nextTick(function () {
            requestAnimationFrame(function () {
              var months = self.$root.querySelectorAll("section[data-cm-more]");
              for (var i = 0; i < months.length; i++) {
                if (!self.monthVisible(months[i])) continue;
                var h = months[i].querySelector("h2");
                if (h && h.focus) { if (!h.hasAttribute("tabindex")) h.setAttribute("tabindex", "-1"); h.focus(); }
                return;
              }
            });
          });
        },
        /* A link's target in the list — a card (or anything in it), a month (its heading), a section of cards (the
           monthly series, the weekly meetings) — → what to bring into view, after clearing the filters and opening the
           fold so it shows; null for anything else (the browser's own jump is enough) and for a card whose time has
           passed. A target the card does not show (a series' date after the three it lists, the anchors of the
           committee meeting's and the Grapevine Meeting's dates) brings the card itself. */
        go: function (id) {
          var el = id && document.getElementById(id);
          if (!el || !this.$root.contains(el)) return null;
          var card = el.closest("li[data-group]"), month = el.closest("[data-cm-month]") || el.closest("#ev-pinned") || el.closest("#ev-weekly");
          if (card && !live(card)) return null;
          if (!card && !month) return null;
          if (el.closest("[data-cm-more]")) this.more = true;
          if (card ? !this.picked(card) : !this.monthVisible(month)) this.clear();
          return card || el;
        },
        /* Bring it into view once it shows (Alpine's x-show shows an element on the next animation frame: after
           its update, $nextTick, one more frame), mark its card a moment (.cm-flash: committee.css; a month heading
           is not marked) and move the keyboard there without scrolling again */
        reveal: function (el) {
          /* (round 37's fixer) The cards are drawn only near the screen (committee.css content-visibility: auto —
             until then each counts a guessed height): a card far down the list landed above or below the screen once
             the browser drew those around it at their real heights ("See all events" on a 2027 event's page). So
             for the jump every card is drawn (.cm-cv-all), it scrolls once the layout is real and once more after
             it settles; a card once drawn keeps its real height (contain-intrinsic-block-size: auto …), so the class
             can go a moment later without moving anything. */
          var root = this.$root;
          if (root && root.classList) {
            root.classList.add("cm-cv-all");
            clearTimeout(root.__cmCvAll);
            root.__cmCvAll = setTimeout(function () { root.classList.remove("cm-cv-all"); }, 1500);
          }
          this.$nextTick(function () {
            requestAnimationFrame(function () {
              if (el.scrollIntoView) el.scrollIntoView({ block: "start" });
              // (where it is on the screen — an old browser without it: no second scroll)
              var topOf = function () { return el.getBoundingClientRect ? el.getBoundingClientRect().top : 0; };
              var at = topOf();
              requestAnimationFrame(function () {
                requestAnimationFrame(function () {
                  if (el.scrollIntoView && Math.abs(topOf() - at) > 2) el.scrollIntoView({ block: "start" });
                });
              });
              var box = el.querySelector("article") || el.closest("article");
              if (box) {
                clearTimeout(box.__cmFlash);
                box.classList.remove("cm-flash");
                void box.offsetWidth; // (a second link to the same card starts the mark again)
                box.classList.add("cm-flash");
                box.__cmFlash = setTimeout(function () { box.classList.remove("cm-flash"); }, 2400);
              }
              if (!el.hasAttribute("tabindex")) el.setAttribute("tabindex", "-1");
              try { el.focus({ preventScroll: true }); } catch (e) { /* an old browser: the scroll above stays */ }
            });
          });
        },
      };
    });

    /* /meetings/#grapevine-meetings: filters for the Grapevine meetings (city / county / group, day,
       in person / online, nearby areas on or off) and "Meets today" (Central time).
       One card per group (li[data-gvg]: data-area, data-days, data-q = folded text); inside, rows of
       weekdays (data-days) with time chips ([data-slot]: data-att, data-n = how many meetings the
       chip stands for — one per weekday of its row). A card shows when its text and area match and
       at least one of its times matches the day and in person / online; those rows and times are
       highlighted. Empty regions and the whole "Nearby areas" block hide with their cards.
       Phones (< 640px, committee.css): "Filters" (moreOpen) folds the day / in person / nearby
       controls; each region shows 3 cards (data-fold on the others) + "Show all N groups"
       (toggleRegion); the nearby areas fold behind one button (nearOpen). While searching or
       filtering by day / in person nothing is folded, so every match shows.
       Without JavaScript the filters stay hidden (committee.css, html.js) and every group shows. */
    Alpine.data("cmGvMeetings", function () {
      function fold(s) {
        return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/\s+/g, " ").trim();
      }
      function days(el) { return (el.getAttribute("data-days") || "").split(" ").filter(Boolean); }
      function plural(el, pre, n) { return String(el.getAttribute(pre + (n === 1 ? "-one" : "-many")) || "{n}").replace("{n}", n); }
      // today's weekday in Central time, 0 = Sunday
      function weekday() {
        try {
          return ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].indexOf(new Intl.DateTimeFormat("en-US", { timeZone: TZ, weekday: "short" }).format(new Date()));
        } catch (e) { return new Date().getDay(); }
      }
      return {
        day: "", q: "", how: "", nearby: true, today: -1, shown: 0, groups: 0, total: 0, labels: { many: "{n}", one: "{n}" },
        moreOpen: false, nearOpen: false, open: {}, regionN: {},
        init: function () {
          var root = this.$root, self = this;
          this.labels = countLabels(root);
          this.total = Number(root.getAttribute("data-total")) || 0;
          this.shown = this.total;
          this.groups = root.querySelectorAll("li[data-gvg]").length;
          this.today = weekday();
          this.markToday();
          this.fold();
          // a page left open past midnight moves "Meets today" to the new day
          this._t = setInterval(function () { var d = weekday(); if (d !== self.today) { self.today = d; self.markToday(); } }, 60000);
          this.$watch("day", function () { self.apply(); });
          this.$watch("q", function () { self.apply(); });
          this.$watch("how", function () { self.apply(); });
          this.$watch("nearby", function () { self.apply(); });
          // The hero card's "Grapevine meetings · Today: N" link (gvmTeaser below): show today's
          // meetings — the Day filter set to today, the other filters cleared
          window.addEventListener("cm:gvm-day", function (e) {
            self.q = ""; self.how = ""; self.nearby = true; self.day = String(e.detail);
          });
          // A link to one group (#gvg-…, the site search) or to one of its meetings (#mtg-…, older
          // links): bring the group's card into view and outline it
          var id = "";
          try { id = location.hash ? decodeURIComponent(location.hash.slice(1)) : ""; } catch (e) {}
          var card = null;
          if (id.indexOf("gvg-") === 0) card = document.getElementById(id);
          else if (/^mtg-[a-z0-9-]+$/i.test(id)) card = root.querySelector('li[data-mtg~="' + id + '"]');
          if (card && root.contains(card)) {
            if (id.indexOf("mtg-") === 0) card.classList.add("is-target");
            // on a phone the card may be folded away (a region's 4th card on, or the nearby areas):
            // unfold its region / the nearby block first
            if (card.getAttribute("data-area") === "nearby") this.nearOpen = true;
            var rid = this.regionOf(card);
            if (rid) this.open[rid] = true;
            this.fold();
            this.$nextTick(function () { card.scrollIntoView({ block: "center" }); });
          }
        },
        destroy: function () { clearInterval(this._t); },
        // "Meets today" on the cards of the groups that meet today, today's row in blue, and
        // "(today)" after today's name in the Day list
        markToday: function () {
          var t = String(this.today), root = this.$root;
          root.querySelectorAll("li[data-gvg]").forEach(function (card) {
            var on = days(card).indexOf(t) !== -1;
            card.classList.toggle("is-today", on);
            var b = card.querySelector("[data-gvm-today]");
            if (b) b.hidden = !on;
          });
          root.querySelectorAll(".cm-gvg-row").forEach(function (row) { row.classList.toggle("is-today", days(row).indexOf(t) !== -1); });
          var tpl = root.getAttribute("data-today-label") || "{day}";
          root.querySelectorAll('select[x-model="day"] option[data-name]').forEach(function (o) {
            var name = o.getAttribute("data-name");
            o.textContent = o.value === t ? tpl.replace("{day}", name) : name;
          });
        },
        get filtered() { return this.day !== "" || this.q.trim() !== "" || this.how !== "" || !this.nearby; },
        // a search or a day / in person filter: every match shows (nothing folded on phones)
        get searching() { return this.day !== "" || this.q.trim() !== "" || this.how !== ""; },
        // how many of the folded filters (behind "Filters" on phones) are set
        get moreCount() { return (this.day !== "" ? 1 : 0) + (this.how !== "" ? 1 : 0) + (this.nearby ? 0 : 1); },
        regionOf: function (el) { var r = el && el.closest ? el.closest("[data-gvm-group]") : null; return r ? r.getAttribute("data-gvm-group") : ""; },
        isOpen: function (el) { return !!this.open[this.regionOf(el)]; },
        foldable: function (el) { return !this.searching && (this.regionN[this.regionOf(el)] || 0) > 3; },
        foldLabel: function (el) {
          var id = this.regionOf(el), b = el && el.closest ? el.closest("[data-more]") : null;
          if (!b) return "";
          return this.open[id] ? b.getAttribute("data-less") : String(b.getAttribute("data-more") || "").replace("{n}", this.regionN[id] || 0);
        },
        toggleRegion: function (el) {
          var id = this.regionOf(el);
          if (!id) return;
          this.open[id] = !this.open[id];
          this.fold();
        },
        // Phones: a region shows its first 3 visible cards (the rest get data-fold, hidden by
        // committee.css below 640px) unless it is open or a search / filter is on.
        fold: function () {
          var self = this, all = this.searching;
          this.$root.querySelectorAll(".cm-gvg-region").forEach(function (reg) {
            var id = reg.getAttribute("data-gvm-group"), k = 0, open = all || !!self.open[id];
            reg.querySelectorAll("li[data-gvg]").forEach(function (li) {
              var vis = !li.hidden;
              li.toggleAttribute("data-fold", vis && !open && k >= 3);
              if (vis) k++;
            });
            self.regionN[id] = k;
          });
        },
        get statusText() { return countText(this.labels, this.shown).replace("{groups}", plural(this.$root, "data-groups", this.groups)); },
        reset: function () {
          this.day = ""; this.q = ""; this.how = ""; this.nearby = true;
          // the pressed button hides itself: keep keyboard focus in the filters, not on <body>
          var f = this.$root.querySelector("input[type=search]");
          if (f) this.$nextTick(function () { f.focus(); });
        },
        apply: function () {
          var root = this.$root, self = this, shown = 0, groups = 0;
          var terms = fold(this.q).split(" ").filter(Boolean);
          var day = String(this.day), how = this.how, slotFilter = day !== "" || how !== "";
          root.querySelectorAll("li[data-gvg]").forEach(function (card) {
            var ok = self.nearby || card.getAttribute("data-area") === "ours";
            var text = card.getAttribute("data-q") || "";
            for (var i = 0; ok && i < terms.length; i++) if (text.indexOf(terms[i]) === -1) ok = false;
            var n = 0;
            card.querySelectorAll(".cm-gvg-row").forEach(function (row) {
              var dayOk = day === "" || days(row).indexOf(day) !== -1, rowHit = false;
              row.querySelectorAll("[data-slot]").forEach(function (chip) {
                var att = chip.getAttribute("data-att");
                var hit = dayOk && !(how === "in_person" && att === "online") && !(how === "online" && att === "in_person");
                chip.classList.toggle("is-match", slotFilter && hit);
                if (hit) { rowHit = true; n += day === "" ? Number(chip.getAttribute("data-n")) || 1 : 1; }
              });
              row.classList.toggle("is-match", slotFilter && rowHit);
            });
            ok = ok && n > 0;
            card.hidden = !ok;
            if (ok) { shown += n; groups++; }
            card._gvN = ok ? n : 0;
          });
          // regions (and our Area): hide when empty, say what is left
          root.querySelectorAll("[data-gvm-group]").forEach(function (g) {
            var cards = g.querySelectorAll("li[data-gvg]:not([hidden])"), m = 0;
            for (var j = 0; j < cards.length; j++) m += cards[j]._gvN;
            g.hidden = !cards.length;
            var c = g.querySelector("[data-gvm-count]");
            if (c) c.textContent = plural(root, "data-groups", cards.length) + " · " + plural(root, "data-meetings", m);
          });
          // the regions left share the rows again (the same rules as packRegions in eleventy/filters/committee.js)
          root.querySelectorAll("[data-gvm-regions]").forEach(function (grid) {
            var regions = [];
            Array.prototype.forEach.call(grid.children, function (r) {
              if (!r.hidden) regions.push({ el: r, cards: r.querySelectorAll("li[data-gvg]:not([hidden])") });
            });
            // the grid rows a region takes: its head + 4 per row of cards
            regions.forEach(function (x) {
              var n = x.cards.length;
              for (var C = 1; C <= 4; C++) x.el.style.setProperty("--h" + C, 1 + 4 * (n >= C ? Math.ceil(n / C) : 1));
            });
            // every card is one column wide (committee.css); a region spans the whole row when it has a
            // row of cards or more, else just its cards, so small regions sit side by side
            [2, 3, 4].forEach(function (C) {
              regions.forEach(function (x) {
                var n = x.cards.length;
                x.el.style.setProperty("--r" + C, n && n < C ? (n * 12) / C : 12);
              });
            });
          });
          var nb = root.querySelector("[data-gvm-nearby]");
          if (nb) nb.hidden = !nb.querySelector("li[data-gvg]:not([hidden])");
          this.shown = shown;
          this.groups = groups;
          this.fold();
        },
      };
    });

    /* /photos/ album: "Show all" reveals the photos the CSS hides (committee.css, photo grid)
       and moves keyboard focus to the first photo that was hidden — the button disappears,
       so focus would otherwise be lost. x-data="cmAlbum()" on the album <section>. */
    Alpine.data("cmAlbum", function () {
      return {
        all: false,
        showAll: function () {
          var first = null;
          var items = this.$root.querySelectorAll(".cm-photo-grid > li");
          for (var i = 0; i < items.length; i++) {
            if (getComputedStyle(items[i]).display === "none") { first = items[i]; break; }
          }
          this.all = true;
          this.$nextTick(function () {
            var a = first && first.querySelector("a");
            if (a) a.focus();
          });
        },
      };
    });

    /* /photos/#covers: the magazine covers' filter — Magazine (All · Grapevine · La Viña), Decade (All · 2020s …
       1940s), and Year and Month (one list each: a year straight away, a month alone — every April — or a year and
       a month), chips like /events/' (cmEvents: counts in .cm-chip-count, a chip that reaches 0 hides, "All" takes
       over) and /listen/'s rows (a pressed chip pressed again lets go). x-data="cmCovers()" on <section id="covers">;
       its blocks are section[data-cm-cover] (data-mag "gv" | "lv", data-year, data-count = its covers), shown by
       shows($el); each cover's <li> says the months its issue covers (data-months "4", La Viña's "3 4").
       A year says its decade (choosing 1966 presses 1960s; another decade lets the year go; All decades lets both
       go). A Month hides the covers of other months inside the blocks (their <li> hidden) and a block left with
       none, and the section flows its blocks' covers as ONE grid (photos.njk :class "is-flat", committee.css).
       Every choice counts what it would show with the others: the Decade chips (the magazine and month), the Year
       list (the magazine and month — a year outside the chosen decade still shows: choosing it moves the decade),
       the Month list (the magazine, decade and year); a year or month with none is greyed out (disabled). The
       Magazine chips count the whole collections. When a choice leaves a combination with no covers (another
       magazine), the year goes first, then the decade, then the month.
       The address keeps the filter (?mag=gv&decade=1960&year=1966&month=4 — no decade beside a year; history.
       replaceState: no extra Back steps; a value the page has no covers for is left out): a search result or a share
       opens on the same view. A link into the covers sets it too — #covers-gv / #covers-lv: that magazine (the
       album index's collection cards), #covers-gv-2019: that magazine and year (the decade with it, no month); any
       other id inside a block (its generic anchors: "album-grapevine-covers-2019", What's New's "grapevine-covers-
       2019") that the filter hides: the filter is reset — then the target is brought into view (on load, and on
       every hashchange: the browser could not scroll to a hidden block). Once a choice was made, a link into one
       block in the address becomes "#covers" (it would set the filter back).
       A link that sets the filter (#covers-gv, #covers-lv-2019, and #covers itself while a filter is on — the address's
       ?mag=lv&year=2019#covers-lv-2019 of a search result) lands on the FILTER (.cm-covers-filter: its pressed chips
       and "Clear filters" in view, the block right under them); a block's generic id lands on that block.
       With no filter on, the earlier years are folded away (`folded`: the blocks with data-cm-early — every year but
       the 2 newest, photos.njk / coverShelf): "Show earlier years (2015–2024)" (showEarlier) shows them for the rest
       of the visit (`all`) — a filter shows every block it matches, and clearing it folds them away again until the
       visitor has asked for them; a link to a folded block shows them too. Until this runs, committee.css hides the
       folded blocks from the first paint (:root.js:not(.cm-covers-ready)), so the page does not jump.
       The live region says "Showing 12 covers" only after the visitor changed something.
       Without JavaScript the filter and the button are hidden ([data-js-only]) and every block shows. */
    Alpine.data("cmCovers", function () {
      var MAGS = ["gv", "lv"];
      function hashId() {
        try { return location.hash ? decodeURIComponent(location.hash.slice(1)) : ""; } catch (e) { return ""; }
      }
      // 1966 → "1960" ("" without a year)
      function decadeOf(y) { return /^\d{4}$/.test(String(y || "")) ? String(Math.floor(Number(y) / 10) * 10) : ""; }
      function isMonth(m) { return /^(?:[1-9]|1[0-2])$/.test(String(m || "")); }
      function hasMonth(li, m) { return (" " + (li.getAttribute("data-months") || "") + " ").indexOf(" " + m + " ") !== -1; }
      return {
        mag: "", decade: "", year: "", month: "", touched: false, all: false, labels: { many: "{n}", one: "{n}" },
        init: function () {
          var self = this;
          this.labels = countLabels(this.$root);
          this.readUrl();
          var target = this.go(hashId());
          this.recount();
          this.syncUrl();
          // x-show now owns what is folded away: drop the first-paint rule (committee.css .cm-covers-ready)
          this.$nextTick(function () { document.documentElement.classList.add("cm-covers-ready"); });
          if (target) this.reveal(target);
          window.addEventListener("hashchange", function () {
            var el = self.go(hashId());
            if (el) self.reveal(el);
          });
        },
        /* Bring a link's target into view once its block shows: Alpine's x-show shows an element on the next
           animation frame (it hides at once), so after its update ($nextTick) one more frame */
        reveal: function (el) {
          this.$nextTick(function () { requestAnimationFrame(function () { el.scrollIntoView({ block: "start" }); }); });
        },
        blocks: function () { return this.$root.querySelectorAll("[data-cm-cover]"); },
        /* a block's covers of each month ({ "4": 1 }) — read once from its <li data-months> */
        monthsIn: function (b) {
          if (!b._cmMonths) {
            var m = {};
            b.querySelectorAll("li").forEach(function (li) {
              String(li.getAttribute("data-months") || "").split(/\s+/).forEach(function (k) { if (k) m[k] = (m[k] || 0) + 1; });
            });
            b._cmMonths = m;
          }
          return b._cmMonths;
        },
        /* a block's covers that a filter f ({ mag, decade, year, month } — "" = any) shows: 0 when the block is
           not one of its magazine, decade and year */
        coversOf: function (b, f) {
          var y = b.getAttribute("data-year") || "";
          if ((f.mag && b.getAttribute("data-mag") !== f.mag) || (f.year && y !== f.year) || (f.decade && decadeOf(y) !== f.decade)) return 0;
          return f.month ? (this.monthsIn(b)[f.month] || 0) : (Number(b.getAttribute("data-count")) || 0);
        },
        state: function () { return { mag: this.mag, decade: this.decade, year: this.year, month: this.month }; },
        /* how many covers a filter would show: the current one with some choices changed (`change`) */
        count: function (change) {
          var self = this, f = this.state(), n = 0;
          for (var k in change || {}) f[k] = String(change[k] || "");
          this.blocks().forEach(function (b) { n += self.coversOf(b, f); });
          return n;
        },
        shows: function (el) {
          return this.coversOf(el, this.state()) > 0 && !(this.folded && el.hasAttribute("data-cm-early"));
        },
        /* the covers on screen */
        get visibleCount() {
          var self = this, f = this.state(), n = 0;
          this.blocks().forEach(function (b) { if (self.shows(b)) n += self.coversOf(b, f); });
          return n;
        },
        get filtered() { return this.mag !== "" || this.decade !== "" || this.year !== "" || this.month !== ""; },
        /* no filter on and the earlier years not asked for: only the 2 newest years show */
        get folded() { return !this.all && !this.filtered; },
        /* "Show earlier years (2015–2024)": the rest shows, and the keyboard goes on to the first cover that was
           folded away (the pressed button disappears) */
        showEarlier: function () {
          var first = this.$root.querySelector("[data-cm-early]");
          this.touched = true;
          this.all = true;
          this.syncUrl();
          var a = first && first.querySelector("a.cm-photo");
          if (a && a.focus) this.$nextTick(function () { a.focus(); });
        },
        countText: function () { return this.touched ? countText(this.labels, this.visibleCount) : ""; },
        setMag: function (m) {
          this.touched = true;
          this.mag = MAGS.indexOf(m) !== -1 && this.count({ mag: m, decade: "", year: "", month: "" }) ? m : "";
          this.recount();
          this.syncUrl();
        },
        /* a decade chip: the year goes when it is another decade's; All decades lets the year go too */
        setDecade: function (d) {
          this.touched = true;
          d = String(d || "");
          if (/^\d{3}0$/.test(d) && this.count({ decade: d, year: "" })) {
            this.decade = d;
            if (this.year && decadeOf(this.year) !== d) this.year = "";
          } else {
            this.decade = ""; this.year = "";
          }
          this.recount();
          this.syncUrl();
        },
        /* a year: its decade with it; All years keeps the decade */
        setYear: function (y) {
          this.touched = true;
          y = String(y || "");
          if (/^\d{4}$/.test(y) && this.count({ year: y, decade: "" })) { this.year = y; this.decade = decadeOf(y); } else this.year = "";
          this.recount();
          this.syncUrl();
        },
        setMonth: function (m) {
          this.touched = true;
          m = String(m || "").replace(/^0/, "");
          this.month = isMonth(m) && this.count({ month: m }) ? m : "";
          this.recount();
          this.syncUrl();
        },
        clear: function () {
          this.touched = true;
          this.mag = ""; this.decade = ""; this.year = ""; this.month = "";
          this.recount();
          this.syncUrl();
          // the pressed "Clear filters" hides itself: keep keyboard focus in the filter (its first chip)
          var first = this.$root.querySelector('[data-cm-mag=""]');
          if (first && first.focus) this.$nextTick(function () { first.focus(); });
        },
        /* What every choice would show now (above) — and a choice left with no covers lets go (the year first,
           then the decade, then the month); a Month hides the other months' covers inside the blocks */
        recount: function () {
          var self = this;
          if (this.year && !this.count({ month: "" })) this.year = "";
          if (this.year) this.decade = decadeOf(this.year);
          if (this.decade && !this.count({ year: "", month: "" })) this.decade = "";
          if (this.month && !this.count()) this.month = "";
          this.$root.querySelectorAll("[data-cm-decade]").forEach(function (chip) {
            var d = chip.getAttribute("data-cm-decade"), n = self.count({ decade: d, year: "" });
            var c = chip.querySelector(".cm-chip-count");
            if (c) c.textContent = n;
            if (d) chip.hidden = !n;
          });
          // the lists' options: "1966 (12)", "April (78)" — greyed out with none
          var opt = function (o, n) {
            o.textContent = (o.getAttribute("data-label") || "") + " (" + n + ")";
            o.disabled = !n;
          };
          this.$root.querySelectorAll("[data-cm-year]").forEach(function (o) { opt(o, self.count({ year: o.getAttribute("data-cm-year"), decade: "" })); });
          this.$root.querySelectorAll("[data-cm-month]").forEach(function (o) { opt(o, self.count({ month: o.getAttribute("data-cm-month") })); });
          // A Month: the other months' covers hide, and the slideshow goes through the covers on screen — every
          // April, one after another — not the year block each one is in. GLightbox groups by data-gallery: with a
          // Month the covers on screen share "covers-month", in the page's order (the order they flow in on the
          // flat grid, .is-flat: the newest year first, Grapevine before La Viña in a year, the newest issue first);
          // every other cover goes out of it, into its block's id + "-off" — the other months' covers AND every
          // cover of a block that the Magazine, Decade or Year hides. (Round 33c: before, only the month was looked
          // at, so ?year=1948&month=9 showed 1 cover and a slideshow of 93 — every September of every year, both
          // magazines — and Next went to "Grapevine — September 1947", not on screen.) "On screen" is the block's
          // own x-show test (shows(): the filter's state, so it is right before Alpine has drawn the change) and
          // the cover's month (li.hidden). No Month: each cover back in its own block's slideshow (data-cm-gallery:
          // the gallery the page gave it) — a block then shows whole or not at all, so that is the covers on
          // screen too, and its "Full screen" button opens it.
          var m = this.month, moved = false;
          this.blocks().forEach(function (b) {
            var on = !!m && self.shows(b);
            b.querySelectorAll("li").forEach(function (li) {
              li.hidden = !!m && !hasMonth(li, m);
              var a = li.querySelector("a.glightbox-cm");
              if (!a) return;
              if (!a.hasAttribute("data-cm-gallery")) a.setAttribute("data-cm-gallery", a.getAttribute("data-gallery") || "");
              var own = a.getAttribute("data-cm-gallery"), g = !m ? own : on && !li.hidden ? "covers-month" : own + "-off";
              if (a.getAttribute("data-gallery") !== g) { a.setAttribute("data-gallery", g); moved = true; }
            });
          });
          // GLightbox reads each link's gallery when it starts (getElements): read them again. (Not its reload():
          // that would add a second click handler.) Before it starts there is nothing to do.
          var lb = window.CM && window.CM.lightbox;
          if (moved && lb && typeof lb.getElements === "function") {
            try { lb.elements = lb.getElements(); } catch (e) { /* the slideshow still opens, by year */ }
          }
        },
        readUrl: function () {
          var p;
          try { p = new URLSearchParams(location.search); } catch (e) { return; }
          var m = p.get("mag") || "", d = p.get("decade") || "", y = p.get("year") || "", mo = String(p.get("month") || "").replace(/^0/, "");
          if (MAGS.indexOf(m) !== -1 && this.count({ mag: m })) this.mag = m;
          if (/^\d{4}$/.test(y) && this.count({ year: y })) { this.year = y; this.decade = decadeOf(y); }
          else if (/^\d{3}0$/.test(d) && this.count({ decade: d })) this.decade = d;
          if (isMonth(mo) && this.count({ month: mo })) this.month = mo;
        },
        syncUrl: function () {
          var p;
          try { p = new URLSearchParams(location.search); } catch (e) { return; }
          // always in this order (mag, decade, year, month), whatever was chosen first; a year says its decade
          ["mag", "decade", "year", "month"].forEach(function (k) { p.delete(k); });
          if (this.mag) p.set("mag", this.mag);
          if (this.decade && !this.year) p.set("decade", this.decade);
          if (this.year) p.set("year", this.year);
          if (this.month) p.set("month", this.month);
          var qs = p.toString(), h = location.hash || "";
          var t = this.touched && h && document.getElementById(hashId());
          if (t && t !== this.$root && this.$root.contains(t)) h = "#covers";
          var url = location.pathname + (qs ? "?" + qs : "") + h;
          if (url === location.pathname + location.search + location.hash) return;
          try { history.replaceState(history.state, "", url); } catch (e) { /* a sandboxed frame: the filter still works */ }
        },
        /* A link into the covers (see above): set the filter so its target shows → what to scroll to — the filter
           when the link set it (a magazine, a magazine and year) or #covers while a filter is on, else the target —,
           or null when the id is not in the covers section. */
        go: function (id) {
          var el = id && document.getElementById(id);
          if (!el || !this.$root.contains(el)) return null;
          var m = /^covers-(gv|lv)(?:-(\d{4}))?$/.exec(id), toFilter = false;
          if (m && this.count({ mag: m[1], decade: "", year: "", month: "" })) {
            this.mag = m[1];
            this.year = m[2] && this.count({ mag: m[1], decade: "", year: m[2], month: "" }) ? m[2] : "";
            this.decade = decadeOf(this.year);
            this.month = "";
            toFilter = true;
          } else {
            var block = el.closest("[data-cm-cover]");
            if (block && !this.shows(block)) {
              this.mag = ""; this.decade = ""; this.year = ""; this.month = "";
              if (!this.shows(block)) this.all = true;     // an earlier year, folded away: show them
            }
            toFilter = el === this.$root && this.filtered;
          }
          this.recount();
          this.syncUrl();
          var bar = toFilter && this.$root.querySelector(".cm-covers-filter");
          // A filter taller than half the screen (a phone at large text) would leave the covers the link was for
          // below the fold: then the link's own target (the magazine's / year's block) instead.
          if (bar && el !== this.$root && typeof bar.getBoundingClientRect === "function" && window.innerHeight &&
              bar.getBoundingClientRect().height > window.innerHeight / 2) bar = null;
          return bar || el;
        },
        /* A block's ↑ (href "#covers"): the hashchange above brings the filter into view — but when the address
           already ends in #covers (a second ↑) there is no hashchange and the browser would only jump to the
           section's top, so do it here */
        up: function (e) {
          if (location.hash !== "#covers") return;
          if (e) e.preventDefault();
          var el = this.go("covers");
          if (el) this.reveal(el);
        },
      };
    });

    /* /portfolio/ category toggles + quick search */
    Alpine.data("cmDocs", function () {
      return {
        tab: "all", q: "", labels: { many: "{n}", one: "{n}" },
        init: function () {
          this.labels = countLabels(this.$root);
          var m = location.hash.match(/^#docs-(.+)$/);
          if (m && document.getElementById("docs-" + m[1])) this.tab = m[1];
        },
        set: function (k) {
          this.tab = k;
          try { history.replaceState(null, "", k === "all" ? location.pathname + location.search : "#docs-" + k); } catch (e) {}
        },
        terms: function () { return this.q.toLowerCase().trim().split(/\s+/).filter(Boolean); },
        match: function (el) {
          var t = this.terms();
          if (!t.length) return true;
          var txt = el.getAttribute("data-text") || "";
          for (var i = 0; i < t.length; i++) if (txt.indexOf(t[i]) === -1) return false;
          return true;
        },
        sectionVisible: function (key, count, el) {
          if (this.tab !== "all") return this.tab === key;
          if (!count) return false;
          if (!this.q) return true;
          var self = this;
          return Array.prototype.some.call(el.querySelectorAll("li[data-text]"), function (li) { return self.match(li); });
        },
        get visibleCount() {
          var self = this, tab = this.tab;
          return Array.prototype.filter.call(this.$root.querySelectorAll("li[data-text]"), function (li) {
            var sec = li.closest("section");
            if (tab !== "all" && sec && sec.id !== "docs-" + tab) return false;
            return self.match(li);
          }).length;
        },
        countText: function () { return countText(this.labels, this.visibleCount); },
      };
    });
  });

  /* ---------------- dropdown menus (<details class="cm-menu">) ---------------- */
  function closeMenus(except) {
    document.querySelectorAll("details.cm-menu[open]").forEach(function (d) { if (d !== except) d.removeAttribute("open"); });
  }
  document.addEventListener("click", function (e) {
    var menu = e.target.closest && e.target.closest("details.cm-menu");
    closeMenus(menu);
    if (menu && e.target.closest(".cm-menu-panel a")) setTimeout(function () { menu.removeAttribute("open"); }, 0);
  });
  /* An event card's "Add to calendar" menu on /events/ (events.njk calMenu), as it opens — since round 35. The page
     carries brief Google / Outlook links (title, times, place: eleventy/filters/committee.js calendarLinks brief) so
     that a reader running no script (an AI tool's fetch) is not mostly link addresses; here they become the full ones,
     with the description, from the card's own .ics data (data-cm-ics: the title, times, place and description the
     build used — CM.calLinks makes the very addresses calendarLinks makes). And the menu's note gets its words from
     the one copy on the agenda (data-cm-note="timed" | "day" → its data-cm-note-timed / -day). A menu without
     data-cm-ics (the pinned cards: Alpine's :href) is left as it is, and so is a note already written (an event's own
     page, whose links are the full ones already: they get the same addresses again). Before the panel is placed
     (below): the note changes its size. */
  function fillMenu(d) {
    var b = d.querySelector("[data-cm-ics]");
    if (b && !d._cmFull) {
      try {
        var links = CM.calLinks(JSON.parse(b.getAttribute("data-cm-ics")));
        var g = d.querySelector('a[href^="https://calendar.google.com/"]'), o = d.querySelector('a[href^="https://outlook.live.com/"]');
        if (g) g.setAttribute("href", links.gcal);
        if (o) o.setAttribute("href", links.outlook);
        d._cmFull = true;
      } catch (err) { /* malformed data: the brief links stay, and work */ }
    }
    var note = d.querySelector(".cm-menu-note[data-cm-note]");
    if (note && !note.textContent) {
      var key = "data-cm-note-" + note.getAttribute("data-cm-note"), src = note.closest("[" + key + "]");
      if (src) note.textContent = src.getAttribute(key) || "";
    }
  }
  // Keep an opened menu on the screen: it opens under its button, aligned left; if that
  // would run past the right edge (a button far right on a phone), align it right, and if
  // it then starts off the left edge, pin it 8px from the edge. "toggle" does not bubble,
  // so it is caught in the capture phase.
  document.addEventListener("toggle", function (e) {
    var d = e.target;
    if (!d || !d.matches || !d.matches("details.cm-menu") || !d.open) return;
    fillMenu(d);
    var panel = d.querySelector(".cm-menu-panel");
    if (!panel) return;
    panel.style.left = ""; panel.style.right = "";
    var M = 8, vw = document.documentElement.clientWidth, r = panel.getBoundingClientRect();
    if (r.right > vw - M) { panel.style.left = "auto"; panel.style.right = "0"; r = panel.getBoundingClientRect(); }
    if (r.left < M) { panel.style.right = "auto"; panel.style.left = (M - d.getBoundingClientRect().left) + "px"; }
  }, true);
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    var open = document.querySelector("details.cm-menu[open]");
    if (open) { open.removeAttribute("open"); var s = open.querySelector("summary"); if (s) s.focus(); }
  });

  /* ---------------- per-event .ics download ----------------
     Bound on each button (NOT delegated to document): Chromium silently drops
     the synthetic <a download>.click() when it is fired from a document-level
     click listener, so delegation would break the download. */
  function bindIcsButtons() {
    document.querySelectorAll("[data-cm-ics]").forEach(function (b) {
      if (b._cmBound) return;
      b._cmBound = true;
      b.addEventListener("click", function (e) {
        e.preventDefault();
        try { CM.downloadIcs(JSON.parse(b.getAttribute("data-cm-ics"))); } catch (err) { /* malformed data: ignore */ }
        closeMenus();
      });
    });
  }

  /* ---------------- Drive preview dialog ---------------- */
  var lastTrigger = null;
  function dialogEl() { return document.getElementById("cm-preview"); }
  CM.preview = function (src, title, openUrl, downloadUrl) {
    var dlg = dialogEl();
    if (!dlg || typeof dlg.showModal !== "function" || !src) return false;
    var frame = dlg.querySelector("iframe");
    var h = dlg.querySelector("#cm-preview-title");
    var o = dlg.querySelector("[data-cm-open]");
    var dl = dlg.querySelector("[data-cm-download]");
    if (h) h.textContent = title || h.textContent;
    if (o) { o.href = openUrl || src; }
    if (dl) { if (downloadUrl) { dl.href = downloadUrl; dl.hidden = false; } else { dl.hidden = true; dl.removeAttribute("href"); } }
    dlg.classList.remove("is-loaded");
    frame.setAttribute("title", title || "");
    frame.onload = function () { dlg.classList.add("is-loaded"); };
    frame.src = src;
    dlg.showModal();
    document.documentElement.style.overflow = "hidden";
    return true;
  };
  document.addEventListener("click", function (e) {
    var t = e.target.closest && e.target.closest("[data-cm-preview]");
    if (!t || e.metaKey || e.ctrlKey || e.shiftKey || e.button > 0) return;
    lastTrigger = t;
    if (CM.preview(t.getAttribute("data-cm-preview"), t.getAttribute("data-cm-title"), t.getAttribute("data-cm-open"), t.getAttribute("data-cm-download"))) e.preventDefault();
  });
  function wireDialog() {
    var dlg = dialogEl();
    if (!dlg) return;
    dlg.addEventListener("click", function (e) {
      if (e.target === dlg || (e.target.closest && e.target.closest("[data-cm-close]"))) dlg.close();
    });
    dlg.addEventListener("close", function () {
      var f = dlg.querySelector("iframe");
      if (f) f.src = "about:blank";
      document.documentElement.style.overflow = "";
      if (lastTrigger && document.contains(lastTrigger)) lastTrigger.focus();
    });
  }

  /* ---------------- hide things whose time has passed ----------------
     Pages are rebuilt daily; this keeps them right between builds.
     [data-cm-expire="ISO"] → hidden once that moment passes (data-cm-expired) — but never under the
     reader: the element that holds keyboard focus (a link or button inside an event card, a meeting
     date) waits until focus leaves it, then goes (app.js GV.expire's rule).
     [data-cm-max="6"] on a list → only the first N non-expired children show. */
  function holdsFocus(el) {
    var a = document.activeElement;
    return !!(a && a !== document.body && el.contains(a));
  }
  function afterFocus(el) {                            // try again once focus has moved on
    if (el.__cmExpireWait) return;
    el.__cmExpireWait = true;
    el.addEventListener("focusout", function () {
      el.__cmExpireWait = false;
      setTimeout(expire, 0);
    }, { once: true });
  }
  function expire() {
    var now = Date.now(), hid = 0;
    document.querySelectorAll("[data-cm-expire]").forEach(function (el) {
      var t = Date.parse(el.getAttribute("data-cm-expire"));
      if (!t || t > now || el.hasAttribute("data-cm-expired")) return;
      if (holdsFocus(el)) { afterFocus(el); return; }
      el.setAttribute("data-cm-expired", "");
      el.hidden = true;
      hid++;
    });
    // /events/' chips and "Showing N events" are counted again (cmEvents)
    if (hid) { try { window.dispatchEvent(new CustomEvent("cm:expired", { detail: hid })); } catch (e) { /* very old browser */ } }
    document.querySelectorAll("[data-cm-max]").forEach(function (list) {
      var max = Number(list.getAttribute("data-cm-max")) || 6, i = 0;
      Array.prototype.forEach.call(list.children, function (li) {
        if (li.hasAttribute("data-cm-expired")) return;
        li.classList.toggle("hidden", i >= max);
        li.classList.toggle("is-next", i === 0);
        i++;
      });
    });
  }

  /* ---------------- /events/: the "Next 5 weeks" calendar (events.njk #ev-cal [data-cm-cal]) ----------------
     The build draws the weeks from the Sunday of its own week, its today and the day whose list shows; the page
     may be read days later (built daily; an offline copy), so the browser keeps it true to today, in Central time:
       · the rows: expire() above — each <tr data-cm-expire="the end of its Saturday"> goes once its week is over,
         and the tbody's data-cm-max="5" shows the first five rows left (three spare rows wait, hidden);
       · calToday() (at start and every minute): .is-today + aria-current="date" on today's cell, .is-past on the
         days before it — whose link goes (no href: its events' cards have left the list) —; an entry of a day's
         list whose time is over is faded and loses its link (.is-over), and a day's link leads to its first entry
         still to come; the list shown stays current — the visitor's pick until that day is over, else today's
         while something is still on today, else the next day with something on ("Today" / "Next up" before its
         date); the month caption is written again for the rows shown once the first of them has changed
         (Intl's month range, as the build's: "November – December 2026");
       · a click on a day (a link to its first card, where it goes without JavaScript) shows that day's list
         instead (.is-selected on the day; the list's region is aria-live, so a screen reader reads it); a click
         on an entry follows its link to the card — the list (cmEvents) reveals a card it hides, on hashchange;
         when the address already ends in that card's #id there is no hashchange, so this says "cm:reveal"
         ({ id }) and cmEvents answers it the same way.
     Nothing here changes the layout: the cells keep their size, the list's region its place. */
  var calSel = null;   // the day whose list shows: { ymd, auto } — auto: chosen by calToday, not by the visitor
  function calRoot() { return document.querySelector("[data-cm-cal]"); }
  function calPanel(cal, ymd) { return ymd ? cal.querySelector('[data-cm-cal-panel="' + ymd + '"]') : null; }
  function calShow(cal, ymd, auto) {
    var box = cal.querySelector("[data-cm-cal-panels]"), today = chicagoYmd(new Date());
    cal.querySelectorAll("[data-cm-cal-panel]").forEach(function (p) {
      var on = p.getAttribute("data-cm-cal-panel") === ymd;
      if (p.hidden !== !on) p.hidden = !on;
      var tag = p.querySelector("[data-cm-cal-tag]");
      var txt = on && box ? (ymd === today ? box.getAttribute("data-today") : auto ? box.getAttribute("data-next") : "") || "" : "";
      // (written only when it changes: a live region reads out every new text)
      if (tag && tag.textContent !== txt) tag.textContent = txt;
    });
    cal.querySelectorAll("[data-cm-day]").forEach(function (td) { td.classList.toggle("is-selected", td.getAttribute("data-cm-day") === ymd); });
    calSel = { ymd: ymd, auto: !!auto };
  }
  // "November – December 2026" for two "YYYY-MM-DD" days (the build: committee.js calendarWeeks' caption)
  function monthRange(a, b) {
    try {
      var f = new Intl.DateTimeFormat(LOCALE, { month: "long", year: "numeric", timeZone: "UTC" });
      var x = new Date(a + "T12:00:00Z"), y = new Date(b + "T12:00:00Z");
      return cap(f.formatRange ? f.formatRange(x, y) : f.format(x) + " – " + f.format(y));
    } catch (e) { return ""; }
  }
  function calToday() {
    var cal = calRoot();
    if (!cal) return;
    var now = Date.now(), today = chicagoYmd(new Date(now));
    cal.querySelectorAll("[data-cm-day]").forEach(function (td) {
      var ymd = td.getAttribute("data-cm-day"), past = ymd < today;
      td.classList.toggle("is-today", ymd === today);
      td.classList.toggle("is-past", past);
      if (ymd === today) { if (td.getAttribute("aria-current") !== "date") td.setAttribute("aria-current", "date"); }
      else if (td.hasAttribute("aria-current")) td.removeAttribute("aria-current");
      var a = past && td.querySelector("a[href]");
      if (a) a.removeAttribute("href");
    });
    cal.querySelectorAll("[data-cm-cal-end]").forEach(function (li) {
      var end = Date.parse(li.getAttribute("data-cm-cal-end"));
      if (!end || end > now || li.classList.contains("is-over")) return;
      li.classList.add("is-over");
      var a = li.querySelector("a[href]");
      if (a) a.removeAttribute("href");
    });
    cal.querySelectorAll("a[data-cm-cal-day]").forEach(function (a) {
      var p = a.hasAttribute("href") && calPanel(cal, a.getAttribute("data-cm-cal-day"));
      var first = p && p.querySelector("a[href]");
      if (first && a.getAttribute("href") !== first.getAttribute("href")) a.setAttribute("href", first.getAttribute("href"));
    });
    // the list shown
    if (!calSel || calSel.auto || calSel.ymd < today) {
      var pick = "";
      cal.querySelectorAll("[data-cm-cal-panel]").forEach(function (p) {
        var ymd = p.getAttribute("data-cm-cal-panel");
        if (pick || ymd < today) return;
        if (Array.prototype.some.call(p.querySelectorAll("[data-cm-cal-end]"), function (li) { return !li.classList.contains("is-over"); })) pick = ymd;
      });
      calShow(cal, pick, true);
    } else calShow(cal, calSel.ymd, calSel.auto);
    // the month caption, for the rows shown
    var capEl = cal.querySelector("[data-cm-cal-cap]");
    var rows = Array.prototype.filter.call(cal.querySelectorAll("tr[data-cm-expire]"), function (tr) { return !tr.hidden && !tr.classList.contains("hidden"); });
    if (capEl && rows.length) {
      var a1 = rows[0].querySelector("[data-cm-day]"), z = rows[rows.length - 1].querySelectorAll("[data-cm-day]");
      var from = a1 && a1.getAttribute("data-cm-day"), to = z.length && z[z.length - 1].getAttribute("data-cm-day");
      if (from && to && from !== capEl.getAttribute("data-cm-cal-cap")) {
        var txt = monthRange(from, to);
        if (txt) { capEl.textContent = txt; capEl.setAttribute("data-cm-cal-cap", from); }
      }
    }
  }
  function calendar() {
    var cal = calRoot();
    if (!cal) return;
    // below 1024px the calendar is folded under its heading (committee.css: .is-open shows it): its button opens and
    // closes it, saying which it does; from 1024px the button is hidden and the calendar always shows
    var fold = cal.querySelector("[data-ev-cal-toggle]");
    if (fold) {
      fold.addEventListener("click", function () {
        var open = !cal.classList.contains("is-open");
        cal.classList.toggle("is-open", open);
        fold.setAttribute("aria-expanded", String(open));
        var label = fold.querySelector("[data-ev-cal-label]");
        if (label) label.textContent = fold.getAttribute(open ? "data-hide" : "data-show") || label.textContent;
      });
    }
    cal.querySelectorAll("[data-cm-cal-panel]").forEach(function (p) {
      if (!p.hidden && !calSel) calSel = { ymd: p.getAttribute("data-cm-cal-panel"), auto: true };
    });
    cal.addEventListener("click", function (e) {
      var a = e.target && e.target.closest ? e.target.closest("a") : null;
      if (!a) return;
      var day = a.getAttribute("data-cm-cal-day");
      if (day) {
        if (!a.hasAttribute("href") || !calPanel(cal, day)) return;
        e.preventDefault();
        // (the day already shown on its own stays so: "Next up" keeps its word)
        calShow(cal, day, !!(calSel && calSel.auto && calSel.ymd === day));
        return;
      }
      var href = a.getAttribute("href") || "", id = "", cur = "";
      if (href.charAt(0) !== "#" || !a.closest("[data-cm-cal-panel]")) return;
      try { id = decodeURIComponent(href.slice(1)); cur = decodeURIComponent((location.hash || "").slice(1)); } catch (err) { return; }
      if (id && id === cur) { try { window.dispatchEvent(new CustomEvent("cm:reveal", { detail: { id: id } })); } catch (err) { /* very old browser */ } }
    });
    calToday();
  }

  /* ---------------- Grapevine Weekly Open: next date ----------------
     The page is built daily, but the meeting is weekly: roll the date forward
     in the browser, say "Live now" during the meeting, and add the visitor's
     own time when they are outside Central time.
     <p data-cm-weekly="ISO" data-cm-weekly-tz="America/New_York" data-cm-weekly-at="12:00" data-cm-weekly-len="60">…
     <span data-cm-weekly-label data-live="…">…
     <span data-cm-weekly-date>…<span data-cm-weekly-local data-tpl="Your time: {time}" hidden>
     data-cm-weekly-len (minutes): the date line gives the end too — "Wednesday, October 7 · 11:00 AM – 12:00 PM CDT". */

  // Next start of a weekly meeting at a fixed local time, stepping calendar weeks in the
  // host's zone: Noon Eastern stays 11 AM Central across daylight-saving changes
  // (same as nextWeeklyStart in eleventy/filters/committee.js; the zone math: GVTime).
  function nextWeekly(t, now, tz, at, live) {
    var p = T && T.zoneParts(t, tz);
    if (!p && T) { tz = TZ; at = ""; p = T.zoneParts(t, tz); } // unknown zone name → Central, keeping t's clock time
    if (!p) { while (t + live < now) t += 7 * 864e5; return t; } // no Intl time zones at all
    var m = /^(\d{1,2}):(\d{2})$/.exec(String(at || "").trim());
    var h = m ? Number(m[1]) : p.h, mi = m ? Number(m[2]) : p.mi;
    for (var w = 1; t + live < now && w < 5000; w++) t = T.zoneInstant(p.y, p.mo, p.d + 7 * w, h, mi, tz);
    return t;
  }

  // A meeting that has not started yet (La Viña's Reunión Abierta, from its first date) carries
  // data-cm-weekly-starts="ISO of the first meeting": until then the build's own "Starts Thursday,
  // November 5, 2026" line stays as it is; from that moment on it reads like the other one
  // ("Live now" / "Next meeting: …" — the label's data-next).
  function weekly() {
    document.querySelectorAll("[data-cm-weekly]").forEach(function (box) {
      var t = Date.parse(box.getAttribute("data-cm-weekly"));
      if (!t) return;
      var now = Date.now(), LIVE = 75 * 60000;
      var first = Date.parse(box.getAttribute("data-cm-weekly-starts") || "");
      var before = first && now < first;
      if (before) t = first;
      else t = nextWeekly(t, now, box.getAttribute("data-cm-weekly-tz") || TZ, box.getAttribute("data-cm-weekly-at") || "", LIVE);
      var d = new Date(t), live = now >= t;
      var lab = box.querySelector("[data-cm-weekly-label]");
      if (lab && !before) {
        if (!lab.hasAttribute("data-next")) lab.setAttribute("data-next", lab.textContent);
        lab.textContent = live ? (lab.getAttribute("data-live") || lab.getAttribute("data-next")) : lab.getAttribute("data-next");
      }
      box.classList.toggle("is-live", !before && live);
      var dt = box.querySelector("[data-cm-weekly-date]");
      // data-cm-weekly-short (the /meetings/ hero card, a narrow column): "Wed, Sep 30 · 11:00 AM CDT"
      var short = box.hasAttribute("data-cm-weekly-short");
      var len = Number(box.getAttribute("data-cm-weekly-len")) || 0;
      var when = len > 0 ? range(d, new Date(t + len * 60000)) : fmt(d, { hour: "numeric", minute: "2-digit", timeZoneName: "short" });
      if (dt && !before) dt.textContent = cap(fmt(d, short ? { weekday: "short", month: "short", day: "numeric" } : { weekday: "long", month: "long", day: "numeric" })) + " · " + when;
      var loc = box.querySelector("[data-cm-weekly-local]");
      if (loc) {
        try {
          var tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
          var probe = { hour: "numeric", minute: "numeric", day: "numeric" };
          if (tz && fmt(d, probe, tz) !== fmt(d, probe, TZ)) {
            loc.textContent = String(loc.getAttribute("data-tpl") || "{time}").replace("{time}", fmt(d, { weekday: "short", hour: "numeric", minute: "2-digit", timeZoneName: "short" }, tz));
            loc.hidden = false;
          } else loc.hidden = true;
        } catch (e) { loc.hidden = true; }
      }
    });
  }

  /* ---------------- photo lightbox (GLightbox) ---------------- */
  function initLightbox() {
    if (typeof window.GLightbox !== "function" || !document.querySelector(".glightbox-cm")) return;
    var lab = document.getElementById("cm-lb-i18n");
    // (the labels are text: escaped, so a quote or "<" in a translation can never break the markup)
    var L = function (k, d) { return escAttr((lab && lab.getAttribute("data-" + k)) || d); };
    var html = '<div id="glightbox-body" class="glightbox-container cm-lightbox" tabindex="-1" role="dialog" aria-modal="true" aria-label="' + L("label", "Photos") + '">' +
      '<div class="gloader visible"></div><div class="goverlay"></div><div class="gcontainer">' +
      '<div id="glightbox-slider" class="gslider"></div>' +
      '<button class="gclose gbtn" aria-label="' + L("close", "Close") + '" data-taborder="3">{closeSVG}</button>' +
      '<button class="gprev gbtn" aria-label="' + L("prev", "Previous") + '" data-taborder="2">{prevSVG}</button>' +
      '<button class="gnext gbtn" aria-label="' + L("next", "Next") + '" data-taborder="1">{nextSVG}</button>' +
      "</div></div>";
    /* The keyboard, in and out (GLightbox 3.3 does neither by itself). On open the focus goes into the slideshow —
       to the dialog itself (#glightbox-body, tabindex="-1": a screen reader hears "Photos, dialog"), not behind it on
       the photo; Tab then goes Next → Previous → Close and round again, as GLightbox's own Tab key does. (Not straight
       onto Close: GLightbox's Tab key keeps the focus on its three buttons only once it has put it there itself — it
       marks that button .focused —, so Tab from a Close focused by a script would walk out into the page behind,
       hidden from screen readers.) On close the focus goes back to what opened it — the photo, or
       the album's "Full screen" button — so the next Tab goes on from there, not from the top of the page. The
       opener is the last photo or "Full screen" a person clicked or pressed Enter on (a trusted click: "Full screen"
       opens its first photo with a click of its own, which must not count). Only one slide is there for a screen
       reader at a time: the others (their pictures are drawn see-through, the ones not loaded yet have an empty
       heading) are inert and aria-hidden, again after every change of slide. */
    var opener = null;
    document.addEventListener("click", function (e) {
      if (!e.isTrusted || !e.target || !e.target.closest) return;
      var t = e.target.closest(".glightbox-cm, [data-cm-open-gallery]");
      if (t) opener = t;
    }, true);
    function oneSlide() {
      var box = document.getElementById("glightbox-body");
      if (!box || !lb) return;
      // (by index, as GLightbox finds its slide: with no animation the slide's "current" mark comes after this runs)
      var cur = box.querySelectorAll(".gslide")[lb.index];
      box.querySelectorAll(".gslide").forEach(function (s) {
        if (s === cur) { s.removeAttribute("inert"); s.removeAttribute("aria-hidden"); }
        else { s.setAttribute("inert", ""); s.setAttribute("aria-hidden", "true"); }
      });
    }
    function focusNoScroll(el) {
      try { el.focus({ preventScroll: true }); } catch (e) { el.focus(); }
    }
    var lb = window.GLightbox({
      selector: ".glightbox-cm",
      touchNavigation: true,
      keyboardNavigation: true,
      loop: true,
      zoomable: true,
      draggable: true,
      closeOnOutsideClick: true,
      descPosition: "bottom",
      moreLength: 0,
      openEffect: REDUCED ? "none" : "zoom",
      closeEffect: REDUCED ? "none" : "zoom",
      slideEffect: REDUCED ? "none" : "slide",
      lightboxHTML: html,
      onOpen: function () {
        oneSlide();
        var box = document.getElementById("glightbox-body");
        if (box) focusNoScroll(box);
      },
      afterSlideChange: oneSlide,
      onClose: function () {
        var t = opener;
        opener = null;
        if (t && document.contains(t)) focusNoScroll(t);
      },
    });
    CM.lightbox = lb;
    /* With motion reduced (closeEffect "none") GLightbox 3.3.1 closes at once, in the middle of its own swipe-down
       handler: closing takes the touch handler away (its last position becomes null), and the handler's next line
       then threw "Cannot set properties of null (setting 'x')" on every swipe-to-close. Closing one moment later lets
       the handler finish first; Escape, Close and a tap outside close the same way (GLightbox's own "closing" mark
       makes a second Escape harmless). (typeof: a test's stand-in GLightbox has no close.) */
    if (REDUCED && lb && typeof lb.close === "function") {
      var closeNow = lb.close.bind(lb);
      lb.close = function () { setTimeout(closeNow, 0); };
    }

    // If a full-size Drive image can't load (file not public yet, Google hiccup),
    // GLightbox would spin forever. Fall back to the thumbnail, then to a
    // neutral placeholder, so the slide always finishes loading.
    var thumbs = {};
    document.querySelectorAll(".glightbox-cm").forEach(function (a) {
      var img = a.querySelector("img");
      if (img && img.getAttribute("src")) thumbs[a.href] = img.getAttribute("src");
    });
    var PLACEHOLDER = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600"><rect width="800" height="600" fill="#2a2638"/>' +
      '<g fill="none" stroke="#8a8599" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" transform="translate(340 240)"><rect x="0" y="0" width="120" height="100" rx="12"/><circle cx="38" cy="34" r="12"/><path d="M120 70 88 40 20 100"/></g></svg>');
    document.addEventListener("error", function (e) {
      var img = e.target;
      if (!img || img.tagName !== "IMG" || !img.closest || !img.closest(".gslide")) return;
      var src = img.getAttribute("src") || "";
      var alt = thumbs[src];
      if (alt && !img.hasAttribute("data-cm-fallback")) { img.setAttribute("data-cm-fallback", "thumb"); img.src = alt; }
      else if (img.getAttribute("data-cm-fallback") !== "placeholder") { img.setAttribute("data-cm-fallback", "placeholder"); img.src = PLACEHOLDER; }
    }, true);
    // "Full screen" button: open the album's first photo (bound per button —
    // see bindIcsButtons for why this is not delegated).
    document.querySelectorAll("[data-cm-open-gallery]").forEach(function (b) {
      b.addEventListener("click", function () {
        var first = document.querySelector('.glightbox-cm[data-gallery="' + b.getAttribute("data-cm-open-gallery") + '"]');
        if (first) first.click();
      });
    });
  }

  /* ---------------- committee sub-nav: show "you are here" ----------------
     On phones the pill bar (Meeting · Events · Documents · Photos · Bulletin)
     scrolls sideways and the current tab can start off-screen. Center it inside the
     bar. Only the bar's own scrollLeft changes (scrollIntoView would also move the page). */
  function centerSubnav() {
    var nav = document.querySelector(".cm-subnav-scroll");
    var cur = nav && nav.querySelector(".is-current");
    if (cur && nav.scrollWidth > nav.clientWidth + 1) {
      var n = nav.getBoundingClientRect(), c = cur.getBoundingClientRect();
      var x = nav.scrollLeft + (c.left - n.left - nav.clientLeft) - (nav.clientWidth - c.width) / 2;
      nav.scrollLeft = Math.max(0, Math.min(x, nav.scrollWidth - nav.clientWidth));
    }
    if (nav) subnavEdges(nav);
  }
  /* The bar fades out on the side(s) that still have tabs to scroll to (committee.css .cm-subnav-scroll) */
  function subnavEdges(nav) {
    function mark() {
      var over = nav.scrollWidth > nav.clientWidth + 1;
      nav.classList.toggle("is-overflow", over);
      nav.classList.toggle("at-start", nav.scrollLeft <= 1);
      nav.classList.toggle("at-end", nav.scrollLeft + nav.clientWidth >= nav.scrollWidth - 1);
    }
    mark();
    nav.addEventListener("scroll", mark, { passive: true });
    window.addEventListener("resize", mark);
  }

  /* ---------------- a link to a collapsed disclosure (#how-docs, #share-photos, #how-to-post, #how-events …) ----------------
     opens it (and the <details> it is in), then brings it into view */
  function openTarget() {
    var id = "";
    try { id = location.hash ? decodeURIComponent(location.hash.slice(1)) : ""; } catch (e) {}
    var el = id && document.getElementById(id);
    var d = el && el.closest && el.closest("details");
    if (!d || d.open) return;
    for (var x = d; x; x = x.parentElement && x.parentElement.closest("details")) x.open = true;
    el.scrollIntoView({ block: "start" });
  }
  window.addEventListener("hashchange", openTarget);

  /* ---------------- /bulletin/: "In this post" follows the reading ----------------
     A wide post card lists its sections beside the text (bulletin.njk .cm-ann-toc), in view while the
     post scrolls by. The section being read — the last one whose heading has passed the top of the
     window (under the header: the anchor offset, html scroll-padding-top) — is marked in its list
     (aria-current="true", committee.css), so the list says where you are; at the very bottom of the
     page (it can't scroll further) the last section in view is, since a short last section may never
     reach the top in a tall window. Above the first section (the post's opening lines) nothing is
     marked. Only the mark changes: nothing scrolls, no focus moves. A list that is not shown (a
     narrower card) is left alone. */
  function annToc() {
    var lists = [].slice.call(document.querySelectorAll(".cm-ann-toc")).map(function (nav) {
      var links = [].slice.call(nav.querySelectorAll('a[href^="#"]'));
      return {
        nav: nav, links: links,
        heads: links.map(function (a) {
          var id = "";
          try { id = decodeURIComponent(a.getAttribute("href").slice(1)); } catch (e) {}
          return id ? document.getElementById(id) : null;
        }),
      };
    });
    if (!lists.length) return;
    var queued = false;
    function mark() {
      queued = false;
      var root = document.documentElement, vh = window.innerHeight;
      var line = (parseFloat(getComputedStyle(root).scrollPaddingTop) || 0) + 8;
      var bottom = window.scrollY + vh >= root.scrollHeight - 2;
      lists.forEach(function (l) {
        if (l.nav.offsetParent === null) return;
        var cur = -1, seen = -1;
        l.heads.forEach(function (h, i) {
          if (!h) return;
          var top = h.getBoundingClientRect().top;
          if (top <= line) cur = i;
          if (top < vh) seen = i;
        });
        if (bottom && cur >= 0) cur = seen;
        l.links.forEach(function (a, i) {
          if (i === cur) { if (!a.hasAttribute("aria-current")) a.setAttribute("aria-current", "true"); }
          else if (a.hasAttribute("aria-current")) a.removeAttribute("aria-current");
        });
      });
    }
    function queue() { if (!queued) { queued = true; requestAnimationFrame(mark); } }
    window.addEventListener("scroll", queue, { passive: true });
    window.addEventListener("resize", queue);
    window.addEventListener("gvlv:prefs", queue);   // a text size or spacing change moves every heading
    mark();
  }

  /* ---------------- /meetings/ hero card: how many Grapevine meetings there are today ----------------
     <a data-gvm-today-link …><span data-gvm-today-teaser data-counts="3,2,4,1,5,2,0" (meetings per
     weekday, Sunday first) data-one="Today: 1 meeting" data-many="Today: {n} meetings"
     data-none="None today · {n} this week">{n} a week …</span></a>
     Today is the weekday in Central time. When some meet today the link also sets the list's Day
     filter to today (cmGvMeetings listens for "cm:gvm-day"); without JavaScript it is a plain jump. */
  function gvmTeaser() {
    var el = document.querySelector("[data-gvm-today-teaser]");
    if (!el) return;
    var counts = String(el.getAttribute("data-counts") || "").split(",").map(Number);
    if (counts.length !== 7) return;
    var d;
    try { d = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].indexOf(new Intl.DateTimeFormat("en-US", { timeZone: TZ, weekday: "short" }).format(new Date())); }
    catch (e) { d = new Date().getDay(); }
    if (d < 0) return;
    var n = counts[d] || 0, week = counts.reduce(function (s, x) { return s + (x || 0); }, 0);
    var tpl = n === 1 ? el.getAttribute("data-one") : n ? el.getAttribute("data-many") : el.getAttribute("data-none");
    if (tpl) el.textContent = tpl.replace("{n}", n || week);
    var a = el.closest("[data-gvm-today-link]");
    if (a) a.setAttribute("data-day", n ? String(d) : "");
  }
  document.addEventListener("click", function (e) {
    var a = e.target && e.target.closest && e.target.closest("[data-gvm-today-link]");
    var d = a && a.getAttribute("data-day");
    if (d) window.dispatchEvent(new CustomEvent("cm:gvm-day", { detail: d }));
  });

  /* ---------------- boot ---------------- */
  // Deferred script: the DOM is parsed already; Alpine starts right after us.
  expire();
  calendar();
  weekly();
  gvmTeaser();
  setInterval(function () { expire(); calToday(); weekly(); gvmTeaser(); }, 60000);
  function ready() { centerSubnav(); bindIcsButtons(); wireDialog(); initLightbox(); openTarget(); annToc(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready); else ready();
})();
